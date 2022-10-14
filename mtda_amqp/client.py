import os
import zerorpc
import socket


class Client:

    def __init__(self,remote):

        self.remote=remote
        self.connection = pika.BlockingConnection(pika.URLParameters('amqp://admin:password@%s:5672/%2F',str(self.remote)))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True)
        self.response = None
        self.corr_id = None
        

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, n):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
              exchange='',
              routing_key='mtda-amqp',
              properties=pika.BasicProperties(
                  reply_to=self.callback_queue,
                  correlation_id=self.corr_id,
            ),
        body=str(n))
        self.connection.process_data_events(time_limit=None)
        return self.response



