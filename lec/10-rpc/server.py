import grpc
from concurrent import futures
import math_pb2_grpc
import math_pb2

class Calc(math_pb2_grpc.CalcServicer):
    def Mult(self, request, context):
        # request is a MultRequest obj
        print(request)
        result = request.x * request.y
        return math_pb2.MultResp(result=result)

server = grpc.server(futures.ThreadPoolExecutor(max_workers=10), options=[("grpc.so_reuseport", 0)])

math_pb2_grpc.add_CalcServicer_to_server(Calc(), server)
print("start listening on port 5444")
server.add_insecure_port('localhost:5444')
server.start()
server.wait_for_termination()
