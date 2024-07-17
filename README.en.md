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
from spirems import Core
core = Core()
core.join()
```

2.  Publish topics
```Python
from spirems import Publisher, def_msg
pub = Publisher('/topic/hello', 'std_msgs::String')
msg = def_msg('std_msgs::String')
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
