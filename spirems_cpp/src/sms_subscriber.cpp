#include "sms_subscriber.h"


#define BUFF_SIZE 1024 * 1024


namespace sms {


Subscriber::Subscriber
(
    std::string topic_url, std::string topic_type, void(*callable)(nlohmann::json), 
    std::string ip, int port
)
{
    this->_topic_url = topic_url;
    this->_topic_type = topic_type;
    this->_callable = callable;

    this->_ip = ip;
    this->_port = port;

    this->_last_send_time = 0.0;
    this->_force_quit = false;
    this->_heartbeat_running = false;
    this->_running = true;

    this->_client_socket = -1;
    this->_buf = new char[BUFF_SIZE + 1];
    this->_recv_t = nullptr;
    this->_send_t = nullptr;

    load_msg_types();

    this->_recv_t = new std::thread(&Subscriber::recv_loop, this);
    this->_send_t = new std::thread(&Subscriber::send_loop, this);

    this->_link();
}

Subscriber::~Subscriber()
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

void Subscriber::join()
{
    if (this->_recv_t)
        this->_recv_t->join();
    if (this->_send_t)
        this->_send_t->join();
}

void Subscriber::kill()
{
    if (!this->_force_quit)
    {
        this->_force_quit = true;
        this->_running = false;
        this->_close_socket();
    }
}

void Subscriber::recv_loop()
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
            // std::cout << "recv_loop() -> this->_client_socket < 0" << std::endl;
            this->_heartbeat_running = false;
            sleep(1);
            continue;
        }
        ssize_t buf_len = read(this->_client_socket, this->_buf, BUFF_SIZE);
        if (buf_len <= 0)
        {
            // std::cout << "recv_loop() -> buf_len == 0" << std::endl;
            this->_close_socket();
            this->_heartbeat_running = false;
            sleep(1);
            continue;
        }
        this->_buf[buf_len] = 0;
        std::string data(this->_buf, buf_len);

        std::vector<std::string> checked_msgs;
        std::vector<std::string> parted_msgs;
        std::vector<int> parted_lens;
        std::vector<std::string> recv_msgs;

        _check_msg(data, checked_msgs, parted_msgs, parted_lens);
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

void Subscriber::send_loop()
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
                // std::cout << "send_loop() -> this->_client_socket < 0" << std::endl;
                this->_heartbeat_running = false;
            }
            else
            {
                if (get_time_sec() - this->_last_send_time >= 1.0)
                {
                    this->_heartbeat();
                }
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
            if (n_try > 5)
            {
                n_try = 0;
                this->_link();
            }
        }
    }
}

void Subscriber::suspend()
{
    if (this->_running && this->_heartbeat_running)
    {
        nlohmann::json res_msg = def_msg("_sys_msgs::Suspend");
        std::string bytes = encode_msg(res_msg);

        this->_send_mtx.lock();
        ssize_t ret = send(this->_client_socket, bytes.c_str(), bytes.size(), MSG_NOSIGNAL | MSG_DONTWAIT);
        this->_send_mtx.unlock();

        this->_last_send_time = get_time_sec();
    }
}

void Subscriber::unsuspend()
{
    if (this->_running && this->_heartbeat_running)
    {
        nlohmann::json res_msg = def_msg("_sys_msgs::Unsuspend");
        std::string bytes = encode_msg(res_msg);

        this->_send_mtx.lock();
        ssize_t ret = send(this->_client_socket, bytes.c_str(), bytes.size(), MSG_NOSIGNAL | MSG_DONTWAIT);
        this->_send_mtx.unlock();

        this->_last_send_time = get_time_sec();
    }
}

void Subscriber::_heartbeat()
{
    nlohmann::json heartbeat_msg = def_msg("_sys_msgs::Subscriber");
    heartbeat_msg["topic_type"] = this->_topic_type;
    heartbeat_msg["url"] = this->_topic_url;
    std::string bytes = encode_msg(heartbeat_msg);

    this->_send_mtx.lock();
    ssize_t ret = send(this->_client_socket, bytes.c_str(), bytes.size(), MSG_NOSIGNAL | MSG_DONTWAIT);
    this->_send_mtx.unlock();

    this->_last_send_time = get_time_sec();
}

void Subscriber::_close_socket()
{
	if (this->_client_socket > 0)
    {
		close(this->_client_socket);
	}
	this->_client_socket = -1;
}

bool Subscriber::_link()
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


void Subscriber::_parse_msg(std::string msg)
{
    nlohmann::json json_msg;
    if (decode_msg(msg, json_msg))
    {
        nlohmann::json res_msg = def_msg("_sys_msgs::Result");
        if (json_msg["type"] == "_sys_msgs::TopicDown")
        {
            res_msg["id"] = json_msg["id"];
            std::string bytes = encode_msg(res_msg);

            this->_send_mtx.lock();
            ssize_t ret = send(this->_client_socket, bytes.c_str(), bytes.size(), MSG_NOSIGNAL | MSG_DONTWAIT);
            this->_send_mtx.unlock();

            this->_last_send_time = get_time_sec();
            this->_callable(json_msg["topic"]);
        }
    }
}

}
