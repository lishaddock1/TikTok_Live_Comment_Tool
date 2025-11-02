from mitmproxy import ctx, websocket
import gzip
# 导入主程序中的队列和proto
from main import message_queue, tiktok_pb2

# 保留原始请求头，避免CSP验证问题
def request(flow):
    # 只对TikTok相关域名生效
    if "tiktok.com" in flow.request.url or "byteoversea.com" in flow.request.url or "tiktokcdn.com" in flow.request.url:
        # 保留原始Origin头
        if "Origin" in flow.request.headers:
            flow.request.headers["Origin"] = flow.request.headers["Origin"]
        # 保留原始Referer头
        if "Referer" in flow.request.headers:
            flow.request.headers["Referer"] = flow.request.headers["Referer"]
        # 删除可能暴露代理的头
        if "X-Forwarded-For" in flow.request.headers:
            del flow.request.headers["X-Forwarded-For"]

class TikTokProxyHandler:
    def __init__(self):
        # 拦截TikTok直播的WebSocket连接
        self.target_urls = [
            "tiktok.com/webcast/im/",
            "byteoversea.com/webcast/im/"
        ]

    def websocket_message(self, flow):
        """处理拦截到的WebSocket消息"""
        # 过滤非目标URL的流量
        if not any(url in flow.request.url for url in self.target_urls):
            return
            
        # 只处理服务器发给客户端的消息
        if flow.messages[-1].from_client:
            return

        # 提取原始数据
        raw_data = flow.messages[-1].content
        ctx.log.info(f"拦截到TikTok数据，长度：{len(raw_data)}")
        
        try:
            # 解析推送帧
            push_frame = tiktok_pb2.WebcastPushFrame()
            push_frame.ParseFromString(raw_data)
            
            if push_frame.payload_type == "ack":
                return  # 忽略心跳包
                
            # 处理gzip压缩数据
            if push_frame.headers.get("compress_type") == "gzip":
                uncompressed_data = gzip.decompress(push_frame.payload)
                # 将处理后的数据放入队列
                message_queue.put(uncompressed_data)
                
        except Exception as e:
            ctx.log.error(f"解析错误：{str(e)}")

# 注册插件
addons = [TikTokProxyHandler(), request]
    