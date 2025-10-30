import asyncio
import logging

from grpc import aio

from sqlalchemy.orm import Session
from grpc_database import SessionLocal
from model.payments import Payment
from proto import payment_pb2, payment_pb2_grpc


class PaymentService(payment_pb2_grpc.PaymentServiceServicer):
    async def CreatePayment(self, request, context):
        try:
            if request.amount <= 0:
                return payment_pb2.CreatePaymentRes(
                    payment_id=0,
                    status="FAILED",
                    message="Invalid amount"
                )

            def db_work():
                db: Session = SessionLocal()
                try:
                    # Idempotency check
                    existing = db.query(Payment).filter(
                        Payment.transaction_code == request.booking_reference
                    ).first()

                    if existing:
                        return existing.payment_id, "SUCCESS", "Already processed"

                    p = Payment(
                        payment_status="COMPLETED",
                        payment_method="UPI",  
                        transaction_code=request.booking_reference,
                        amount=request.amount,
                    )
                    db.add(p)
                    db.commit()
                    db.refresh(p)
                    return p.payment_id, "SUCCESS", "Created"
                finally:
                    db.close()

            loop = asyncio.get_running_loop()
            payment_id, status, message = await loop.run_in_executor(None, db_work)

            return payment_pb2.CreatePaymentRes(
                payment_id=payment_id, status=status, message=message
            )

        except Exception as e:
            logging.exception("CreatePayment failed")
            return payment_pb2.CreatePaymentRes(
                payment_id=0, status="FAILED", message=str(e)
            )


async def serve():
    server = aio.server()
    payment_pb2_grpc.add_PaymentServiceServicer_to_server(PaymentService(), server)
    server.add_insecure_port("[::]:50051")

    print("✅ Payment gRPC server listening on :50051")
    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
