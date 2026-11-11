import os
DATABASE_URL=os.getenv("DATABASE_URL","postgresql+psycopg://energy:energy_demo@localhost:17714/energy")
REDIS_URL=os.getenv("REDIS_URL","redis://redis:6379/0")
JWT_SECRET=os.getenv("JWT_SECRET","energy-break-local-demo-change-before-deployment")
SEED_DEMO=os.getenv("SEED_DEMO","true").lower()=="true"
