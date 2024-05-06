#ifndef __SMS_HELPER__
#define __SMS_HELPER__
#include <string>
#include <vector>
#include <nlohmann/json.hpp>


namespace sms {

void get_all_msg_types(std::vector<nlohmann::json>& all_msgs, std::string type_need="");


std::vector<std::string> _split(const std::string& srcstr, const std::string& delimeter);
bool _startswith(const std::string& str, const std::string& start);
bool _endswith(const std::string& str, const std::string& end);
std::string _trim(const std::string& str);

bool _is_file_exist(std::string& fn);
void _list_dir(std::string dir, std::vector<std::string>& files, std::string suffixs="", std::string prefix="", bool r=false);


}


#endif
