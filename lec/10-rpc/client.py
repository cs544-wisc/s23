import grpc
import math_pb2_grpc
import math_pb2

channel = grpc.insecure_channel("localhost:5444")
stub = math_pb2_grpc.CalcStub(channel)
resp = stub.Mult(math_pb2.MultReq(x=3, y=4))
print(resp)
