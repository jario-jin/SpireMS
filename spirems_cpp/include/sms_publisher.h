#ifndef __SMS_PUBLISHER__
#define __SMS_PUBLISHER__


#include "sms_helper.h"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <netdb.h>
#include <thread>
#include <mutex>


namespace sms {


class SentInfo
{
public:
    SentInfo(int uid_, double time_send_, double time_dt_) : uid(uid_), time_send(time_send_), time_dt(time_dt_)
    {
    }
    int uid;
    double time_send;
    double time_dt;
};

class Publisher
{

public:
    Publisher(std::string topic_url, std::string topic_type, std::string ip="127.0.0.1", int port=9094);
    ~Publisher();
    void kill();
    bool publish(nlohmann::json json_msg, bool enforce=false);
    void recv_loop();
    void send_loop();
    void join();

private:
    bool _link();
    void _heartbeat();
    void _close_socket();
    void _parse_msg(std::string msg);
    // void _delay_packet_loss_rate();

    std::string _topic_url;
    std::string _topic_type;
    std::string _ip;
    int _port;
    std::mutex _send_mtx;
    std::mutex _ids_mtx;

    double _last_send_time;
    double _last_upload_time;
    bool _force_quit;
    bool _heartbeat_running;
    bool _running;
    bool _enforce_publish;

    std::string _last_msg;
    int _last_msg_len;
    int _upload_id;
    double _transmission_delay;

    bool _suspended;
    int _error_cnt;
    // std::vector<SentInfo> _uploaded_times;

    int _client_socket;
    struct sockaddr_in _server_addr;
    char* _buf;

    std::thread* _recv_t;
    std::thread* _send_t;
};


}

#endif
