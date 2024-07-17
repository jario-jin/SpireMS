#ifndef __SMS_HELPER__
#define __SMS_HELPER__
#include <string>
#include <vector>
#include <json.hpp>
#include <opencv2/opencv.hpp>


namespace sms {

nlohmann::json def_msg(std::string type_need);
std::vector<nlohmann::json> get_all_msg_types(std::string type_need="");
double get_time_sec();
void msleep(int ms);
bool decode_msg(std::string& byte_msg, nlohmann::json& json_msg);
std::string encode_msg(nlohmann::json& json_msg);
nlohmann::json cvimg2sms(cv::Mat cvimg, std::string encoding="jpg");
cv::Mat sms2cvimg(nlohmann::json msg);

std::string _base64_encode(const std::string& input);
std::string _base64_decode(const std::string& input);
std::string _hex2string(const std::string &hex_data);
int _index_msg_header(std::string& data);
int _decode_msg_header(std::string& data);
void _check_msg(std::string& data, std::vector<std::string>& checked_msgs, std::vector<std::string>& parted_msgs, std::vector<int>& parted_lens);

std::vector<std::string> _split(const std::string& srcstr, const std::string& delimeter);
bool _startswith(const std::string& str, const std::string& start);
bool _endswith(const std::string& str, const std::string& end);
std::string _trim(const std::string& str);

bool _is_file_exist(std::string& fn);
void _list_dir(std::string dir, std::vector<std::string>& files, std::string suffixs="", std::string prefix="", bool r=false);


}


#endif
