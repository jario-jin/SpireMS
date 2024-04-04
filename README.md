# SpireMS

#### 介绍
Spire消息系统，一个类似ROS的轻量化消息发布、订阅软件包，支持图像、雷达等传感器话题。


#### 安装教程

```
pip install spirems
```

#### 使用说明

1.  启动Server
```Python
from spirems import Server
server = Server()
server.start()
```

2.  发布话题
```Python
from spirems import Publisher, get_all_msg_types
pub = Publisher('/topic/hello', 'std_msgs::String')
pub.publish()
msg = get_all_msg_types()['std_msgs::String'].copy()
msg['data'] = 'hello world!'
pub.publish(msg)
```

3.  订阅话题
```Python
from spirems import Subscriber

def callback_f(msg):
    print(msg['data'])

sub = Subscriber('/topic/hello', 'std_msgs::String', callback_f)
```

#### 参与贡献

1.  Fork 本仓库
2.  新建 Feat_xxx 分支
3.  提交代码
4.  新建 Pull Request
