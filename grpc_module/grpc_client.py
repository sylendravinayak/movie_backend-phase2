# quick test client to validate payment service connectivity
import asyncio
import grpc
from proto import payment_pb2, payment_pb2_grpc

TARGET = "127.0.0.1:50051"

async def main():
    async with grpc.aio.insecure_channel(TARGET) as channel:
        try:
            print("Waiting for channel ready...")
            await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
            print("Channel ready, making CreatePayment call...")
        except Exception as e:
            print("Channel ready failed:", e)
            # still try RPC (rpc-level timeout will error if unreachable)
        stub = payment_pb2_grpc.PaymentServiceStub(channel)
        req = payment_pb2.CreatePaymentReq(
            booking_id=9999,
            booking_reference="TEST-REF-123",
            amount=100,
            user_id=1
        )
        try:
            resp = await stub.CreatePayment(req, timeout=5.0)
            print("RPC response:", resp)
        except grpc.aio.AioRpcError as rpc_e:
            print("RPC failed:", rpc_e.code(), rpc_e.details())


if __name__ == "__main__":
    asyncio.run(main())