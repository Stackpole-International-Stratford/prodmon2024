from pubsub import pub

def listener(msg):
    print(msg)


pub.subscribe(listener, 'PING')

msg = {
    'timestamp': 1234567,
    'name': 'test name'
}
pub.sendMessage('PING', msg=msg)

