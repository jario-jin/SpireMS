#ifndef __SMS_PUBLISHER__
#define __SMS_PUBLISHER__


#include "sms_helper.h"
#include <sys/socket.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <netdb.h>
#include <thread>


namespace sms {


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
    void _close_socket();
    void _parse_msg(std::string msg);
    void _delay_packet_loss_rate();

    std::string _topic_url;
    std::string _topic_type;
    std::string _ip;
    int _port;

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
    double _package_loss_rate;

    bool _suspended;
    int _error_cnt;
    std::vector<std::pair<double, double> > _uploaded_times;
    std::vector<int> _uploaded_ids;

    int _client_socket;
    struct sockaddr_in _server_addr;
    char* _buf;
    int _buf_len;

    std::thread* _recv_t;
    std::thread* _send_t;
};


}

#endif
