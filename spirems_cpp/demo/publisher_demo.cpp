#include <iostream>
#include <string>
// 包含SpireMS SDK头文件
#include <sms_core.h>
#include <json.hpp>


using namespace std;


int main(int argc, char *argv[])
{
    // std::vector<nlohmann::json> all_msgs = sms::get_all_msg_types("sensor_msgs::Image");
    // nlohmann::json msg = all_msgs[0];
    sms::Publisher pub("/test/t1", "sensor_msgs::Image", "192.168.88.2");
    int cnt = 0;
    while (1)
    {
        cv::Mat img = cv::imread("/home/jario/Pictures/Screenshots/001.png");
        nlohmann::json msg = sms::cvimg2sms(img);
        // cv::Mat img2 = sms::sms2cvimg(msg);
        // nlohmann::json msg2 = sms::cvimg2sms(img2);
        pub.publish(msg);
        sms::msleep(500);
    }

    pub.join();
    return 0;
}

