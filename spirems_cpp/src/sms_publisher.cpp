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
    this->_buf_len = 0;
    this->_buf = new char[BUFF_SIZE];
    this->_recv_t = nullptr;
    this->_send_t = nullptr;

    this->_error_cnt = 0;
    this->_upload_id = 0;
    this->_transmission_delay = 0.0;
    this->_package_loss_rate = 0.0;

    std::vector<nlohmann::json> all_msgs = get_all_msg_types("");

    this->_recv_t = new std::thread(&Publisher::recv_loop, this);
    this->_send_t = new std::thread(&Publisher::send_loop, this);

    this->_link();
    std::cout << "publish launched!" << std::endl;
}

Publisher::~Publisher()
{
    delete this->_buf;
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

}

bool Publisher::publish(nlohmann::json json_msg, bool enforce)
{
    return true;
}


void Publisher::recv_loop()
{
    while (this->_running)
    {
        std::cout << "_running" << std::endl;
        if (this->_client_socket < 0)
        {
            ;
        }
        size_t buf_len = read(this->_client_socket, this->_buf, BUFF_SIZE);
        if (buf_len == 0)
        {
            ;
        }
        this->_buf[buf_len] = 0;
        std::string data(this->_buf, buf_len);

        nlohmann::json json_msg;
        if (decode_msg(data, json_msg))
            std::cout << json_msg << std::endl;

        sleep(1);
    }
}

void Publisher::send_loop()
{
    while (this->_running)
    {
        std::cout << "_heartbeat_running" << std::endl;
        sleep(1);
    }
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

    if (connect(this->_client_socket, (struct sockaddr*)&this->_server_addr, sizeof(this->_server_addr)) == -1)
    {
		close(this->_client_socket);
		return false;
	}

    return true;
}

void Publisher::_parse_msg(std::string msg)
{

}

void Publisher::_delay_packet_loss_rate()
{
    
}


}
