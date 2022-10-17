#!/usr/bin/env python
import pika
import os


class MTDA_AMQP(object):

    def __init__(self):
        self.connection = pika.BlockingConnection(pika.URLParameters('amqp://admin:password@134.86.62.153:5672'))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue='mtda-amqp')
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(queue='mtda-amqp', on_message_callback=self.on_request)

    def fib(n):
        if n == 0:
            return 0
        elif n == 1:
            return 1
        else:
            return fib(n - 1) + fib(n - 2)

    def target_on(self,args=None):
        result=True
        print("The target is powered on")
        os.system("echo 1 > /sys/class/gpio/gpio201/value")
        os.system("echo 1 > /sys/class/gpio/gpio203/value")
        return result
    
    def target_off(self,args=None):
        result=False
        print("The target is powered off")
        os.system("echo 0 >/sys/class/gpio/gpio201/value")
        os.system("echo 0 >/sys/class/gpio/gpio203/value")
        return result



    def on_request(self,ch, method, props, body):
        if str(body.decode('UTF-8'))=="target_on":
            print(body,type(body))
            response=self.target_on()
        elif str(body.decode('UTF-8'))=="target_off":
            response=self.target_off()
        else:
            response=self.fib(int(body))
        ch.basic_publish(exchange='',routing_key=props.reply_to,properties=pika.BasicProperties(correlation_id =props.correlation_id),body=str(response))
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def run_server(self):
        self.channel.start_consuming()
