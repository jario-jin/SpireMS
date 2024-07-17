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
#include <openssl/bio.h>
#include <openssl/buffer.h>
#include <openssl/evp.h>


namespace sms {


std::vector<nlohmann::json> g_all_msgs;


std::vector<nlohmann::json> get_all_msg_types(std::string type_need)
{
    std::string msgs_path = "/home/jario/deep/spirems/spirems/msgs";

    if (g_all_msgs.size() == 0)
    {
        std::vector<std::string> file_paths;
        _list_dir(msgs_path, file_paths, ".json", "", true);
        for (std::string file_path : file_paths)
        {
            std::ifstream f(file_path);
            nlohmann::json data = nlohmann::json::parse(f);
            g_all_msgs.push_back(data);
            // std::cout << data["type"] << std::endl;
        }
    }
    std::vector<nlohmann::json> res_msgs;
    for (nlohmann::json msg_json : g_all_msgs)
    {
        if (type_need.size() > 0)
        {
            if (type_need == msg_json["type"])
                res_msgs.push_back(msg_json);
        }
        else
        {
            res_msgs.push_back(msg_json);
        }
    }
    return res_msgs;
}


nlohmann::json def_msg(std::string type_need)
{
    std::vector<nlohmann::json> msgs = get_all_msg_types();
    nlohmann::json default_;
    for (nlohmann::json msg_json : g_all_msgs)
    {
        if (type_need == msg_json["type"])
            return msg_json;
        if ("std_msgs::Null" == msg_json["type"])
            default_ = msg_json;
    }
    return default_;
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



cv::Mat sms2cvimg(nlohmann::json msg)
{
    assert(msg["type"] == "sensor_msgs::Image");
    std::string dncoded_base64 = _base64_decode(msg["data"]);

    // QByteArray decoded_base64 = QByteArray::fromBase64(QByteArray::fromStdString(msg["data"].get<std::string>()));
    std::vector<uchar> decoded_vec;
    decoded_vec.assign(dncoded_base64.begin(), dncoded_base64.end());
    cv::Mat cvimg;
    if (msg["encoding"] == "jpeg" || msg["encoding"] == "jpg" || msg["encoding"] == "png")
    {
        cvimg = cv::imdecode(decoded_vec, cv::IMREAD_COLOR);
    }
    return cvimg;
}

nlohmann::json cvimg2sms(cv::Mat cvimg, std::string encoding)
{
    std::vector<uchar> img_encode;
    if (encoding == "jpg" || encoding == "jpeg")
    {
        cv::imencode(".jpg", cvimg, img_encode);
    }
    else if (encoding == "png")
    {
        cv::imencode(".png", cvimg, img_encode);
    }
    std::vector<nlohmann::json> res_msgs = get_all_msg_types("sensor_msgs::Image");
    nlohmann::json img_msg = res_msgs[0];
    img_msg["height"] = cvimg.rows;
    img_msg["width"] = cvimg.cols;
    img_msg["channel"] = 3;
    img_msg["encoding"] = encoding;
    std::string encoded_base64 = std::string(img_encode.begin(), img_encode.end());
    img_msg["data"] = _base64_encode(encoded_base64);
    return img_msg;
}


std::string _base64_encode(const std::string& input)
{
    BUF_MEM* bptr;

    BIO* b64 = BIO_new(BIO_f_base64());
    BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);
    BIO* bmem = BIO_new(BIO_s_mem());
    b64 = BIO_push(b64, bmem);
    BIO_write(b64, input.data(), input.size());
    BIO_flush(b64);
    BIO_get_mem_ptr(b64, &bptr);
    BIO_set_close(b64, BIO_NOCLOSE);

    std::string out;
    out.resize(bptr->length);
    memcpy(&out[0], bptr->data, bptr->length);
    BIO_free_all(b64);

    return out;
}

std::string _base64_decode(const std::string& input)
{
    std::string out;
    out.resize(input.size());

    BIO* b64 = BIO_new(BIO_f_base64());
    BIO_set_flags(b64, BIO_FLAGS_BASE64_NO_NL);
    BIO* bmem = BIO_new_mem_buf(input.data(), input.size());
    bmem = BIO_push(b64, bmem);
    int len = BIO_read(bmem, &out[0], input.size());
    BIO_free_all(bmem);

    out.resize(len);
    return out;
}


}
