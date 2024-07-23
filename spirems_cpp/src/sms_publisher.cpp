#include "sms_publisher.h"
#include <iostream>


#define BUFF_SIZE 1024 * 1024


namespace sms {


Publisher::Publisher(std::string topic_url, std::string topic_type, std::string ip, int port)
{
    this->_topic_url = topic_url;
    this->_topic_type = topic_type;

    this->_ip = ip;
    this->_port = port;

    this->_last_send_time = 0.0;
    this->_last_upload_time = 0.0;
    this->_force_quit = false;
    this->_heartbeat_running = false;
    this->_running = true;
    this->_enforce_publish = false;
    
    this->_client_socket = -1;
    this->_buf = new char[BUFF_SIZE + 1];
    this->_recv_t = nullptr;
    this->_send_t = nullptr;

    this->_error_cnt = 0;
    this->_upload_id = 0;
    this->_transmission_delay = 0.0;

    load_msg_types();

    this->_recv_t = new std::thread(&Publisher::recv_loop, this);
    this->_send_t = new std::thread(&Publisher::send_loop, this);

    this->_link();
}

Publisher::~Publisher()
{
    this->_force_quit = true;
    this->join();
    if (this->_buf)
        delete this->_buf;
    if (this->_recv_t)
        delete this->_recv_t;
    if (this->_send_t)
        delete this->_send_t;
}

void Publisher::join()
{
    if (this->_recv_t)
        this->_recv_t->join();
    if (this->_send_t)
        this->_send_t->join();
}

void Publisher::kill()
{
    if (!this->_force_quit)
    {
        this->_force_quit = true;
        this->_running = false;
        this->_close_socket();
    }
}

bool Publisher::publish(nlohmann::json json_msg, bool enforce)
{
    this->_enforce_publish = enforce;
    if (!this->_suspended && this->_heartbeat_running && (get_time_sec() - this->_last_upload_time > this->_transmission_delay * 0.3 || enforce))
    {
        json_msg["timestamp"] = get_time_sec();
        nlohmann::json topic_upload = def_msg("_sys_msgs::TopicUpload");
        topic_upload["topic"] = json_msg;
        this->_upload_id += 1;
        if (this->_upload_id > 1e6)
            this->_upload_id = 1;
        topic_upload["id"] = this->_upload_id;
        std::cout << "this->_upload_id: "<< this->_upload_id<<", len(this->_uploaded_ids): "<<this->_uploaded_ids.size()<<", (this->_uploaded_times): "<< this->_uploaded_times.size()<< std::endl;

        this->_ids_mtx.lock();
        this->_uploaded_ids.push_back(this->_upload_id);
        this->_uploaded_times.push_back(std::make_pair<double, double>(get_time_sec(), -1));
        this->_ids_mtx.unlock();

        std::string bytes = encode_msg(topic_upload);
        this->_send_mtx.lock();
        ssize_t ret = write(this->_client_socket, bytes.c_str(), bytes.size());
        this->_send_mtx.unlock();

        this->_last_send_time = get_time_sec();
        this->_last_upload_time = get_time_sec();
    }
    return true;
}


void Publisher::recv_loop()
{
    while (this->_running)
    {
        // std::cout << "_running" << std::endl;
        if (this->_force_quit)
        {
            break;
        }
        if (this->_client_socket < 0)
        {
            std::cout << "recv_loop() -> this->_client_socket < 0" << std::endl;
            this->_heartbeat_running = false;
            sleep(1);
            continue;
        }
        ssize_t buf_len = read(this->_client_socket, this->_buf, BUFF_SIZE);
        if (buf_len <= 0)
        {
            std::cout << "recv_loop() -> buf_len == 0" << std::endl;
            this->_heartbeat_running = false;
            sleep(1);
            continue;
        }
        this->_buf[buf_len] = 0;
        std::string data(this->_buf, buf_len);
        std::cout << "buf_len: " << buf_len << std::endl;

        std::vector<std::string> checked_msgs;
        std::vector<std::string> parted_msgs;
        std::vector<int> parted_lens;
        std::vector<std::string> recv_msgs;

        _check_msg(data, checked_msgs, parted_msgs, parted_lens);
        std::cout << "len(this->_last_msg): " << this->_last_msg.size() << ", this->_last_msg_len: " << this->_last_msg_len << std::endl;
        if (parted_msgs.size() > 0)
        {
            for (int i=0; i<parted_msgs.size(); i++)
            {
                if (parted_lens[i] > 0)
                {
                    this->_last_msg = parted_msgs[i];
                    this->_last_msg_len = parted_lens[i];
                }
                else
                {
                    this->_last_msg.append(parted_msgs[i]);
                    if (this->_last_msg_len > 0 && this->_last_msg_len <= this->_last_msg.size())
                    {
                        recv_msgs.push_back(this->_last_msg.substr(0, this->_last_msg_len));
                        this->_last_msg_len = 0;
                        this->_last_msg.clear();
                    }
                }
            }
        }
        for (int i=0; i<checked_msgs.size(); i++)
            recv_msgs.push_back(checked_msgs[i]);

        if (recv_msgs.size() > 0)
        {
            for (int i=0; i<recv_msgs.size(); i++)
                this->_parse_msg(recv_msgs[i]);
        }
    }
}

void Publisher::send_loop()
{
    int n_try = 0;
    while (this->_running)
    {
        // std::cout << "_heartbeat_running" << std::endl;
        while (this->_heartbeat_running)
        {
            if (this->_force_quit)
            {
                break;
            }
            if (this->_client_socket < 0)
            {
                std::cout << "send_loop() -> this->_client_socket < 0" << std::endl;
                this->_heartbeat_running = false;
            }
            else
            {
                if (get_time_sec() - this->_last_send_time >= 1.)
                {
                    this->_heartbeat();
                }
                this->_delay_packet_loss_rate();
            }
            sleep(1);
        }
        if (this->_force_quit)
        {
            break;
        }
        sleep(1);
        if (!this->_heartbeat_running)
        {
            n_try++;
            if (n_try > 10)
            {
                n_try = 0;
                this->_link();
            }
        }
    }
}

void Publisher::_heartbeat()
{
    nlohmann::json heartbeat_msg = def_msg("_sys_msgs::Publisher");
    heartbeat_msg["topic_type"] = this->_topic_type;
    heartbeat_msg["url"] = this->_topic_url;
    heartbeat_msg["enforce"] = this->_enforce_publish;
    std::string bytes = encode_msg(heartbeat_msg);

    this->_send_mtx.lock();
    ssize_t ret = write(this->_client_socket, bytes.c_str(), bytes.size());
    this->_send_mtx.unlock();
    this->_last_send_time = get_time_sec();
}

void Publisher::_close_socket()
{
	if (this->_client_socket > 0)
    {
		close(this->_client_socket);
	}
	this->_client_socket = -1;
}

bool Publisher::_link()
{
    if (this->_client_socket != -1)
    {
		this->_close_socket();
	}
	this->_client_socket = socket(PF_INET , SOCK_STREAM , 0);
	if (this->_client_socket == -1)
    {
		return false;
	}

    memset(&this->_server_addr , 0 , sizeof(this->_server_addr));
	this->_server_addr.sin_family = AF_INET;
	this->_server_addr.sin_port = htons(this->_port);
    inet_pton(AF_INET, this->_ip.c_str(), &this->_server_addr.sin_addr);

    struct timeval timeout;
    timeout.tv_sec = 5;
    timeout.tv_usec = 0;
    if (setsockopt(this->_client_socket, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0)
    {
        this->_close_socket();
		return false;
    }

    if (connect(this->_client_socket, (struct sockaddr*)&this->_server_addr, sizeof(this->_server_addr)) == -1)
    {
		this->_close_socket();
		return false;
	}
    
    this->_last_msg_len = 0;
    this->_last_msg.clear();
    this->_heartbeat();
    this->_heartbeat_running = true;
    return true;
}

void Publisher::_parse_msg(std::string msg)
{
    nlohmann::json json_msg;
    if (decode_msg(msg, json_msg))
    {
        if (json_msg["type"] == "_sys_msgs::Suspend")
        {
            this->_suspended = true;
            // std::cout << "_sys_msgs::Suspend" << std::endl;
        }
        else if (json_msg["type"] == "_sys_msgs::Unsuspend")
        {
            this->_suspended = false;
            // std::cout << "_sys_msgs::Unsuspend" << std::endl;
        }
        else if (json_msg["type"] == "_sys_msgs::Result")
        {
            if (json_msg["id"] > 0)
            {
                this->_error_cnt = 0;
                this->_ids_mtx.lock();
                for (int i=0; i<this->_uploaded_ids.size(); i++)
                {
                    if (json_msg["id"] == this->_uploaded_ids[i])
                    {
                        this->_uploaded_times[i].second = get_time_sec() - this->_uploaded_times[i].first;
                    }
                }
                this->_ids_mtx.unlock();
            }
            if (json_msg["error_code"] > 0)
            {
                this->_error_cnt ++;
                if (this->_error_cnt > 5)
                    this->_suspended = true;
            }
        }
        else if (json_msg["type"] != "_sys_msgs::HeartBeat")
        {
            std::cout << "[SMS_ERROR]: " << json_msg.dump() << std::endl;
        }
    }
}

void Publisher::_delay_packet_loss_rate()
{
    double delay = 0.0;
    int delay_cnt = 0;

    std::vector<int> invalid_ids;

    this->_ids_mtx.lock();
    for (size_t i=0; i<this->_uploaded_times.size(); i++)
    {
        if (this->_uploaded_times[i].second >= 0)
        {
            delay += this->_uploaded_times[i].second;
            delay_cnt ++;
        }
        if (get_time_sec() - this->_uploaded_times[i].first > 5)
        {
            invalid_ids.push_back(i);
        }
    }
    for (size_t i=0; i<invalid_ids.size(); i++)
    {
        if (this->_uploaded_times.size() > 1)
        {
            this->_uploaded_times.erase(this->_uploaded_times.begin() + invalid_ids[i]);
            this->_uploaded_ids.erase(this->_uploaded_ids.begin() + invalid_ids[i]);
        }
        else
        {
            this->_uploaded_times.clear();
            this->_uploaded_ids.clear();
        }
    }
    this->_ids_mtx.unlock();

    if (delay_cnt > 0)
    {
        delay = delay / delay_cnt;
        this->_transmission_delay = delay;
    }

    // std::cout << "this->_transmission_delay: " << this->_transmission_delay << ", size: " << delay_cnt << std::endl;
}


}
