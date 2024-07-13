#include <iostream>
#include <string>
// 包含SpireMS SDK头文件
#include <sms_core.h>
#include <json.hpp>


using namespace std;


int main(int argc, char *argv[])
{
    std::vector<nlohmann::json> all_msgs = sms::get_all_msg_types("_visual_msgs::A2RLMonit");
    cout << all_msgs.size() << endl;
    cout << all_msgs[0] << endl;
    sms::Publisher pub("/test/t1", "std_msgs::Null");
    pub.join();
    return 0;
}

