#include <iostream>
#include <string>
// 包含SpireMS SDK头文件
#include <sms_core.h>
#include <json.hpp>


using namespace std;


void callback(nlohmann::json msg)
{
    cv::Mat img2 = sms::sms2cvimg(msg);
    std::cout << sms::get_time_sec() - msg["timestamp"].get<double>() << std::endl;
    cv::imshow("img2", img2);
    cv::waitKey(10);
}


int main(int argc, char *argv[])
{
    sms::Subscriber sub("/test/t1", "sensor_msgs::CompressedImage", callback);
    sub.join();
    return 0;
}

