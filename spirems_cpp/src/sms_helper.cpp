#include "sms_helper.h"
#include <string>
#include <ctime>
#include <chrono>
#include <fstream>
#include <dirent.h>
#include <unordered_map>
#include <cassert>
#include <cstring>
#include <algorithm>
#include <iostream>
#include <nlohmann/json.hpp>


namespace sms {


void get_all_msg_types(std::vector<nlohmann::json>& all_msgs, std::string type_need)
{
    std::string msgs_path = "/home/jario/spirems/spirems/msgs";

    std::vector<std::string> file_paths;
    _list_dir(msgs_path, file_paths, ".json", "", true);
    for (std::string file_path : file_paths)
    {
        std::ifstream f(file_path);
        nlohmann::json data = nlohmann::json::parse(f);
        if (type_need.size() > 0)
        {
            if (type_need == data["type"])
                all_msgs.push_back(data);
        }
        else
        {
            all_msgs.push_back(data);
        }
        // std::cout << data["type"] << std::endl;
    }
}



std::vector<std::string> _split(const std::string& srcstr, const std::string& delimeter)
{
    std::vector<std::string> ret(0); //use ret save the spilted reault
    if (srcstr.empty())    //judge the arguments
    {
        return ret;
    }
    std::string::size_type pos_begin = srcstr.find_first_not_of(delimeter); //find first element of srcstr

    std::string::size_type dlm_pos; //the delimeter postion
    std::string temp;               //use third-party temp to save splited element
    while (pos_begin != std::string::npos) //if not a next of end, continue spliting
    {
        dlm_pos = srcstr.find(delimeter, pos_begin); //find the delimeter symbol
        if (dlm_pos != std::string::npos)
        {
            temp = srcstr.substr(pos_begin, dlm_pos - pos_begin);
            pos_begin = dlm_pos + delimeter.length();
        }
        else
        {
            temp = srcstr.substr(pos_begin);
            pos_begin = dlm_pos;
        }
        if (!temp.empty())
            ret.push_back(temp);
    }
    return ret;
}

bool _startswith(const std::string& str, const std::string& start)
{
    size_t srclen = str.size();
    size_t startlen = start.size();
    if (srclen >= startlen)
    {
        std::string temp = str.substr(0, startlen);
        if (temp == start)
            return true;
    }

    return false;
}

bool _endswith(const std::string& str, const std::string& end)
{
    size_t srclen = str.size();
    size_t endlen = end.size();
    if (srclen >= endlen)
    {
        std::string temp = str.substr(srclen - endlen, endlen);
        if (temp == end)
            return true;
    }

    return false;
}



bool _is_file_exist(std::string& fn)
{
    std::ifstream f(fn);
    return f.good();
}

void _list_dir(std::string dir, std::vector<std::string>& files, std::string suffixs, std::string prefix, bool r)
{
    // assert(_endswith(dir, "/") || _endswith(dir, "\\"));
    DIR *pdir;
    struct dirent *ent;
    std::string childpath;
    std::string absolutepath;
    pdir = opendir(dir.c_str());
    assert(pdir != NULL);

    std::vector<std::string> suffixd(0);
    // std::cout << suffixs << std::endl;
    if (!suffixs.empty() && suffixs != "") {
        suffixd = _split(suffixs, "|");
    }

    while ((ent = readdir(pdir)) != NULL) {
        if (ent->d_type & DT_DIR) {
            if (strcmp(ent->d_name, ".") == 0 || strcmp(ent->d_name, "..") == 0) {
                continue;
            }
            if (r) { // If need to traverse subdirectories
                childpath = dir + "/" + ent->d_name;
                // std::cout << childpath << std::endl;
                _list_dir(childpath, files, suffixs, prefix, r);
            }
        }
        else {
            if (suffixd.size() > 0) {
                bool can_push = false, cancan_push = true;
                for (int i = 0; i < (int)suffixd.size(); i++) {
                    if (_endswith(ent->d_name, suffixd[i]))
                        can_push = true;
                }
                if (prefix.size() > 0) {
                    if (!_startswith(ent->d_name, prefix))
                        cancan_push = false;
                }
                if (can_push && cancan_push) {
                    absolutepath = dir + ent->d_name;
                    files.push_back(dir + "/" + ent->d_name); // filepath
                }
            }
            else {
                absolutepath = dir + ent->d_name;
                files.push_back(dir + "/" + ent->d_name); // filepath
            }
        }
    }
    sort(files.begin(), files.end()); //sort names
}

}
