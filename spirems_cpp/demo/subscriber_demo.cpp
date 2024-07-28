#include <iostream>
#include <string>
// 包含SpireMS SDK头文件
#include <sms_core.h>
#include <json.hpp>


using namespace std;


void callback(nlohmann::json msg)
{
    cv::Mat img2 = sms::sms2cvimg(msg);
    cv::imshow("img2", img2);
    cv::waitKey(10);
}


int main(int argc, char *argv[])
{
    sms::Subscriber sub("/video_stream/video/image_raw", "sensor_msgs::Image", callback, "192.168.88.9");
    sub.join();
    return 0;
}

