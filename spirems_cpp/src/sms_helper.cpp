#include "sms_helper.h"
#include <string>
#include <ctime>
#include <chrono>
#include <thread>
#include <fstream>
#include <dirent.h>
#include <unordered_map>
#include <cassert>
#include <cstring>
#include <algorithm>
#include <iostream>
#include <json.hpp>
#include <base64.hpp>


namespace sms {


nlohmann::json g_msg_types;


std::string _get_pdir(const std::string& path)
{
    size_t last_slash = path.find_last_of("/\\");
    if (last_slash!= std::string::npos)
    {
        return path.substr(0, last_slash);
    }
    return "";
}


nlohmann::json load_msg_types(std::string msg_type_dir)
{
    if (msg_type_dir.empty())
    {
        if (!g_msg_types.empty())  return g_msg_types;
        std::string type_dir1 = _get_pdir(_get_pdir(_get_pdir(__FILE__))) + "/spirems/msgs";
        std::string type_dir2 = _get_pdir(_get_pdir(_get_pdir(__FILE__))) + "/spirems/json_msgs";
        std::vector<std::string> type_dirs;
        type_dirs.push_back(type_dir1);
        type_dirs.push_back(type_dir2);
        for (std::string type_dir : type_dirs)
        {
            std::vector<std::string> file_paths;
            _list_dir(type_dir, file_paths, ".json", "", true);

            for (std::string file_path : file_paths)
            {
                std::ifstream f(file_path);
                nlohmann::json data = nlohmann::json::parse(f);
                if (data.contains("type") && !g_msg_types.contains(data["type"]))
                {
                    g_msg_types[data["type"]] = data;
                }
            }
        }
    }
    else
    {
        std::vector<std::string> file_paths;
        _list_dir(msg_type_dir, file_paths, ".json", "", true);

        for (std::string file_path : file_paths)
        {
            std::ifstream f(file_path);
            nlohmann::json data = nlohmann::json::parse(f);
            if (data.contains("type") && !g_msg_types.contains(data["type"]))
            {
                g_msg_types[data["type"]] = data;
            }
        }
    }
    if (g_msg_types.empty())
    {
        g_msg_types["std_msgs::Null"] = {
            {"type", "std_msgs::Null"},
            {"timestamp", 0.0}
        };
    }
    return g_msg_types;
}

nlohmann::json def_msg(std::string type_need)
{
    if (g_msg_types.empty())
    {
        load_msg_types();
    }
    if (g_msg_types.contains(type_need))
    {
        return g_msg_types[type_need];
    }
    else
    {
        return g_msg_types["std_msgs::Null"];
    }
}


double get_time_sec()
{
    auto now = std::chrono::system_clock::now();
    auto duration = now.time_since_epoch();
    auto microseconds = std::chrono::duration_cast<std::chrono::microseconds>(duration).count();
    return microseconds / 1e6;
}

void msleep(int ms)
{
    std::this_thread::sleep_for(std::chrono::milliseconds(ms));
}

std::string _hex2string(const std::string &hex_data)
{
    std::stringstream ss;
    for (size_t i=0; i< hex_data.length(); i+=2)
    {
        int hex_value;
        std::stringstream hex_stream(hex_data.substr(i, 2));

        hex_stream >> std::hex >> hex_value;
        ss << static_cast<char>(hex_value);
    }
    return ss.str();
}

std::string _g_msg_header = _hex2string("EAECFBFD");

int _index_msg_header(std::string& data)
{
    int index = -1;
    if (data.size() >= 4)
    {
        index = data.find(_g_msg_header);
    }
    return index;
}


int _decode_msg_header(std::string& data)
{
    int msg_len = 0;
    if (data.size() > 8)
    {
        int* plen = (int*)(data.c_str() + 4);
        msg_len = *plen + 8;
    }
    return msg_len;
}


void _check_msg(std::string& data, std::vector<std::string>& checked_msgs, std::vector<std::string>& parted_msgs, std::vector<int>& parted_lens)
{
    int index = _index_msg_header(data);
    if (index >= 0)
    {
        if (index > 0)
        {
            std::string parted_msg = data.substr(0, index);
            parted_msgs.push_back(parted_msg);
            parted_lens.push_back(0);
        }
        data = data.substr(index, data.length() - index);
        int msg_len = _decode_msg_header(data);
        if (msg_len > 8)
        {
            while (data.size() >= msg_len)
            {
                if (msg_len > 8)
                    checked_msgs.push_back(data.substr(0, msg_len));

                data = data.substr(msg_len, data.length() - msg_len);
                index = _index_msg_header(data);
                if (index >= 0)
                {
                    data = data.substr(index, data.length() - index);
                    msg_len = _decode_msg_header(data);
                    if (msg_len <= 8)
                        break;
                }
                else
                {
                    msg_len = 0;
                    break;
                }
            }
            if (msg_len > 8 && msg_len < 1024 * 1024 * 5)
            {
                parted_msgs.push_back(data);
                parted_lens.push_back(msg_len);
            }
        }
    }
    else if (data.length() > 0)
    {
        parted_msgs.push_back(data);
        parted_lens.push_back(0);
    }
}


std::string encode_msg(nlohmann::json& json_msg)
{
    if (json_msg["timestamp"] == 0.0)
    {
        json_msg["timestamp"] = get_time_sec();
    }
    std::string json_str = json_msg.dump();
    int json_len = json_str.size();

    size_t length = sizeof(int);
    assert(length == 4);
    char *pdata = (char*) &json_len;
    char len_buf[5];
    for (size_t i=0; i<4; i++)
    {
        len_buf[i] = *pdata++;
    }
    len_buf[4] = 0;

    std::string bytes = _g_msg_header + std::string(len_buf, 4) + json_str;
    return bytes;
}


bool decode_msg(std::string& byte_msg, nlohmann::json& json_msg)
{
    bool succ = false;
    if (byte_msg.size() > 8)
    {
        if (byte_msg.substr(0, 4) == _g_msg_header)
        {
            int msg_len = _decode_msg_header(byte_msg);
            if (msg_len == byte_msg.size())
            {
                byte_msg = byte_msg.substr(8, msg_len - 8);
                json_msg = nlohmann::json::parse(byte_msg);
                succ = true;
            }
        }
    }
    return succ;
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
    if (dir.empty())  return;

    DIR *pdir;
    struct dirent *ent;
    std::string childpath;
    std::string absolutepath;
    pdir = opendir(dir.c_str());
    if (!pdir)  return;

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



cv::Mat sms2cvimg(const nlohmann::json& msg)
{
    assert(msg["type"] == "sensor_msgs::CompressedImage");
    std::string dncoded_base64 = _base64_decode(msg["data"]);

    // QByteArray decoded_base64 = QByteArray::fromBase64(QByteArray::fromStdString(msg["data"].get<std::string>()));
    std::vector<uchar> decoded_vec;
    decoded_vec.assign(dncoded_base64.begin(), dncoded_base64.end());
    cv::Mat cvimg;
    if (msg["format"] == "jpeg" || msg["format"] == "jpg" || msg["format"] == "png" || msg["format"] == "webp")
    {
        cvimg = cv::imdecode(decoded_vec, cv::IMREAD_COLOR);
    }
    return cvimg;
}

nlohmann::json cvimg2sms(const cv::Mat& cvimg, const std::string format, const std::string frame_id)
{
    nlohmann::json img_msg = def_msg("sensor_msgs::CompressedImage");
    img_msg["timestamp"] = get_time_sec();
    img_msg["format"] = format;
    img_msg["frame_id"] = frame_id;

    std::vector<uchar> img_encode;
    if (format == "jpg" || format == "jpeg")
    {
        cv::imencode(".jpg", cvimg, img_encode);
    }
    else if (format == "png")
    {
        cv::imencode(".png", cvimg, img_encode);
    }
    else if (format == "webp")
    {
        std::vector<int> quality = {cv::IMWRITE_WEBP_QUALITY, 50};
        cv::imencode(".webp", cvimg, img_encode, quality);
    }
    
    std::string encoded_base64 = std::string(img_encode.begin(), img_encode.end());
    img_msg["data"] = _base64_encode(encoded_base64);
    return img_msg;
}


std::string _base64_encode(const std::string& input)
{
    return base64::to_base64(input);
}

std::string _base64_decode(const std::string& input)
{
    return base64::from_base64(input);
}


}
