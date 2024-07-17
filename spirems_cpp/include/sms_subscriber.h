#ifndef __SMS_SUBSCRIBER__
#define __SMS_SUBSCRIBER__

#include "sms_helper.h"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <netdb.h>
#include <thread>
#include <mutex>


namespace sms {


class Subscriber
{

public:
    Subscriber
    (
        std::string topic_url, std::string topic_type, void(*callable)(nlohmann::json), 
        std::string ip="127.0.0.1", int port=9094
    );
    ~Subscriber();
    void kill();
    void recv_loop();
    void send_loop();
    void join();
    void suspend();
    void unsuspend();

private:
    bool _link();
    void _heartbeat();
    void _close_socket();
    void _parse_msg(std::string msg);

    std::string _topic_url;
    std::string _topic_type;
    void(*_callable)(nlohmann::json msg);
    std::string _ip;
    int _port;
    std::mutex _send_mtx;

    double _last_send_time;
    bool _force_quit;
    bool _heartbeat_running;
    bool _running;

    int _client_socket;
    struct sockaddr_in _server_addr;
    char* _buf;

    std::string _last_msg;
    int _last_msg_len;

    std::thread* _recv_t;
    std::thread* _send_t;
};


}

#endif
