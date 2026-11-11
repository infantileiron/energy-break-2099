import os
DATABASE_URL=os.getenv("DATABASE_URL","postgresql+psycopg://energy:energy_demo@localhost:17714/energy")
REDIS_URL=os.getenv("REDIS_URL","redis://redis:6379/0")
JWT_SECRET=os.getenv("JWT_SECRET","energy-break-local-demo-change-before-deployment")
SEED_DEMO=os.getenv("SEED_DEMO","true").lower()=="true"
# A claimed run is considered abandoned when its lease expires, so another
# worker may resume it using the same run record.
RUN_LEASE_SECONDS=int(os.getenv("RUN_LEASE_SECONDS","15"))
# Stop automatic recovery after this many interrupted claims and expose why.
RUN_MAX_ATTEMPTS=int(os.getenv("RUN_MAX_ATTEMPTS","5"))
