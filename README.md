<img src="https://pic.imgdb.cn/item/66a9ecb5d9c307b7e9059279.png" alt="SpireMS logo" align="right" height="90" />

# SpireMS

## 介绍
Spire消息系统，一个类似ROS的轻量化消息发布、订阅软件包，支持图像、雷达等传感器话题。


## 安装教程

### Python安装

1. 安装（命令行执行）

```Bash
pip install spirems
```

2. 引入（Python代码）

```Python
from spirems import Subscriber, Publisher, def_msg
```

### C++安装（Ubuntu系统）

1. 依赖项安装，如果已经安装cmake、opencv则可以忽略以下2行

```Bash
sudo apt update
sudo apt -y install cmake libopencv-dev
```

2. 源码安装

```Bash
git clone https://gitee.com/jario-jin/spirems.git
cd spirems/spirems_cpp
mkdir build && cd build
cmake ..
sudo make install
```

3. 在自己项目的CMakeLists.txt中引入SpireMS

```
find_package(SpireMS REQUIRED)
include_directories(${SpireMS_INCLUDE_DIRS})
target_link_libraries(YourAppName ${SpireMS_LIBS})
```

## 使用说明

### Python使用说明
1. 启动Core服务（Python交互脚本方式，也可以用C++中的启动方式，启动一次即可）

```Python
from spirems import Core
Core().join()
```

2.  发布话题
```Python
from spirems import Publisher, def_msg
import time
pub = Publisher('/topic/hello', 'std_msgs::String')
msg = def_msg('std_msgs::String')
while True:
    msg['data'] = 'hello world!'
    pub.publish(msg)
    time.sleep(1)
```

3.  订阅话题
```Python
from spirems import Subscriber

def callback_f(msg):
    print(msg['data'])

sub = Subscriber('/topic/hello', 'std_msgs::String', callback_f)
```

### C++使用说明

1. 启动Core服务（命令行方式，也可以用Python中的启动方式，启动一次即可）

```Bash
cd <path-to-spirems>/spirems
python core.py
```

2. 发布话题
```C++
#include <sms_core.h>

int main(int argc, char *argv[])
{
    sms::Publisher pub("/topic/hello", "std_msgs::String");
    nlohmann::json msg = sms::def_msg("std_msgs::String");
    
    while (true)
    {
        msg["data"] = "hello world!";
        pub.publish(msg);
        sleep(1);
    }
}
```

3. 订阅话题
```C++
#include <sms_core.h>

void callback(nlohmann::json msg)
{
    std::cout << msg["data"] << std::endl;
}

int main(int argc, char *argv[])
{
    sms::Subscriber sub("/topic/hello", "std_msgs::String", callback);
    sub.join();
    return 0;
}
```


## 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request
