import gzip
import json
import asyncio
import websockets
from queue import Queue
import threading
import time  # 新增：用于线程中的延迟
from google.protobuf.json_format import MessageToJson
import sys

# 导入proto转换的Python代码
import webcast_pb2 as tiktok_pb2

# WebSocket客户端连接集合
ws_clients = set()
# 消息队列
message_queue = Queue()

class TikTokMessageParser:
    """TikTok消息解析器"""
    def __init__(self):
        self.message_type_map = {
            "WebcastChatMessage": tiktok_pb2.WebcastChatMessage,
            "WebcastMemberMessage": tiktok_pb2.WebcastMemberMessage,
            "WebcastRoomUserSeqMessage": tiktok_pb2.WebcastRoomUserSeqMessage,
            "WebcastLikeMessage": tiktok_pb2.WebcastLikeMessage,
            "WebcastSocialMessage": tiktok_pb2.WebcastSocialMessage,
            "WebcastGiftMessage": tiktok_pb2.WebcastGiftMessage,
            "WebcastImDeleteMessage": tiktok_pb2.WebcastImDeleteMessage,
            "WebcastUnauthorizedMemberMessage": tiktok_pb2.WebcastUnauthorizedMemberMessage,
            "WebcastRankUpdateMessage": tiktok_pb2.WebcastRankUpdateMessage,
            "WebcastLinkMicArmies": tiktok_pb2.WebcastLinkMicArmies,
        }

    def parse_message(self, raw_data):
        """解析原始消息数据"""
        try:
            # 解析推送帧
            push_frame = tiktok_pb2.WebcastPushFrame()
            push_frame.ParseFromString(raw_data)

            if push_frame.payload_type == "ack":
                return  # 忽略心跳包

            # 处理gzip压缩数据
            if push_frame.headers.get("compress_type") == "gzip":
                uncompressed_data = gzip.decompress(push_frame.payload)
                
                # 解析响应消息
                response = tiktok_pb2.WebcastResponse()
                response.ParseFromString(uncompressed_data)

                for msg in response.messages:
                    msg_cls = self.message_type_map.get(msg.method)
                    if not msg_cls:
                        print(f"未知消息类型: {msg.method}", file=sys.stderr)
                        continue

                    # 解析具体消息内容
                    message_obj = msg_cls()
                    message_obj.ParseFromString(msg.payload)
                    
                    # 转换为JSON并放入队列
                    json_data = MessageToJson(message_obj)
                    message_queue.put(json_data)

        except Exception as e:
            print(f"消息解析错误: {str(e)}", file=sys.stderr)

class WebSocketServer:
    """WebSocket服务器，用于向客户端推送消息"""
    def __init__(self, host='0.0.0.0', port=18081):  # 修改端口为18081避免冲突
        self.host = host
        self.port = port
        self.parser = TikTokMessageParser()

    async def register_client(self, websocket):
        """注册新的WebSocket客户端"""
        ws_clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            ws_clients.remove(websocket)

    async def broadcast_messages(self):
        """广播消息队列中的消息到所有客户端"""
        while True:
            if not message_queue.empty():
                message = message_queue.get()
                if ws_clients:
                    # 使用gather并处理可能的连接错误
                    try:
                        await asyncio.gather(
                            *[client.send(message) for client in ws_clients]
                        )
                    except Exception as e:
                        print(f"广播消息错误: {str(e)}", file=sys.stderr)
                message_queue.task_done()
            await asyncio.sleep(0.01)

    async def start_server(self):
        """启动WebSocket服务器"""
        server = await websockets.serve(
            self.register_client, self.host, self.port
        )
        print(f"WebSocket服务器启动在 ws://{self.host}:{self.port}")
        await self.broadcast_messages()

    def run(self):
        """运行WebSocket服务器事件循环"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.start_server())
        except KeyboardInterrupt:
            print("服务器正在关闭...")
        finally:
            loop.close()

def data_feeder(parser):
    """数据 feeder：从队列中获取原始数据并解析"""
    while True:
        if not message_queue.empty():
            raw_data = message_queue.get()
            parser.parse_message(raw_data)
            message_queue.task_done()
        # 使用time.sleep替代asyncio.sleep，因为这是在普通线程中
        time.sleep(0.1)

def main():
    # 启动WebSocket服务器
    ws_server = WebSocketServer(port=18081)  # 修改端口为18081
    
    # 启动数据 feeder 线程
    feeder_thread = threading.Thread(
        target=data_feeder,
        args=(ws_server.parser,),
        daemon=True
    )
    feeder_thread.start()
    
    print(f"WebSocket服务器已启动，等待消息数据... 地址：ws://127.0.0.1:18081")
    ws_server.run()

if __name__ == "__main__":
    main()
    