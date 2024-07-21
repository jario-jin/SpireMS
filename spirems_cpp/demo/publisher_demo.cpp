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
    nlohmann::json msg_types = sms::load_msg_types();
    sms::Publisher pub("/test/t1", "sensor_msgs::Image", "192.168.88.9");
    sms::Subscriber sub("/testcase/num_arr_v2", "std_msgs::Null", callback);
    int cnt = 0;

    cv::VideoCapture cap("/home/jario/Videos/002.mkv");
    cv::Mat img;
    while (1)
    {
        // nlohmann::json msg = sms::def_msg("std_msgs::Null");
        // msg["data"] = "hello";
        cap.read(img);
        if (img.cols == 0 || img.rows == 0)
        {
            cap.set(cv::CAP_PROP_POS_FRAMES, 0);
        }
        else
        {
            nlohmann::json msg = sms::cvimg2sms(img);
            cv::Mat img2 = sms::sms2cvimg(msg);
            nlohmann::json msg2 = sms::cvimg2sms(img2);
            pub.publish(msg2);
        }
        sms::msleep(30);
    }

    pub.join();
    return 0;
}

