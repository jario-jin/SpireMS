# SpireMS

#### Description
Spire message system, a lightweight message publishing and subscription software package similar to ROS, supports topics such as images and radars and other sensors.

#### Installation

```
pip install spirems
```

#### Instructions

1.  Start the server
```Python
from spirems import Server
server = Server()
server.listen()
```

2.  Publish topics
```Python
from spirems import Publisher, get_all_msg_types
pub = Publisher('/topic/hello', 'std_msgs::String')
msg = get_all_msg_types()['std_msgs::String'].copy()
msg['data'] = 'hello world!'
pub.publish(msg)
```

3.  Subscribe to topics
```Python
from spirems import Subscriber

def callback_f(msg):
    print(msg['data'])

sub = Subscriber('/topic/hello', 'std_msgs::String', callback_f)
```

#### Contribution

1.  Fork the repository
2.  Create Feat_xxx branch
3.  Commit your code
4.  Create Pull Request
