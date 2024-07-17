#include <iostream>
#include <string>
// 包含SpireMS SDK头文件
#include <sms_core.h>
#include <json.hpp>


using namespace std;


void callback(nlohmann::json msg)
{
    std::cout << msg["data"] << std::endl;
}


int main(int argc, char *argv[])
{
    sms::Publisher pub("/test/t1", "std_msgs::Null");
    sms::Subscriber sub("/testcase/num_arr_v2", "std_msgs::Null", callback);
    int cnt = 0;

    while (1)
    {
        nlohmann::json msg = sms::def_msg("std_msgs::Null");
        msg["data"] = "hello";
        pub.publish(msg);
        sms::msleep(20);
    }

    pub.join();
    return 0;
}

