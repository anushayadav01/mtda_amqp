#!/usr/bin/env python
import pika


class MTDA_AMQP(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.URLParameters('amqp://admin:password@134.86.62.211:5672/%2F'))
        self.channel = connection.channel()
        self.channel.queue_declare(queue='mtda-amqp')
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='mtda-amqp', on_message_callback=on_request)
        self.channel.start_consuming()



    def fib(n):
        if n == 0:
            return 0
        elif n == 1:
            return 1
        else:
            return fib(n - 1) + fib(n - 2)

    def target_on(self,args=None):
        result=True
        print("The target is power on")
        return result


    def on_request(self,ch, method, props, body):
        print(body,type(body))
        if str(body.decode('UTF-8'))=="target_on":
            response=target_on()
        else:
            response=fib(int(body))
        ch.basic_publish(exchange='',routing_key=props.reply_to,properties=pika.BasicProperties(correlation_id =props.correlation_id),body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        ch.basic_ack(delivery_tag=method.delivery_tag)


