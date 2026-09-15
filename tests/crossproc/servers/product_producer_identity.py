"""The producer's declared identity, shared by the producer process and its consumers.

Constants only — importing this module imports no assembler, no fabric and no
door, which is what lets a consumer test name the producer it expects without
importing `mcp_product_producer` (proof 2 of `D-IMPL-340`: the producer's
assembler is absent from the consumer process).
"""

#: The producer's own tenant — deliberately NOT the consumer fixture's
#: `tenant-fixture`, so the consumer's producer-tenant check has something to
#: hold and a check against the consumer's tenant would visibly refuse.
PRODUCER_TENANT = "producer-fixture"
#: The identity the door asserts, and the one a registration expects.
PRODUCER_ID = "child-product-egress"
#: The logical server name a consumer's registration and binding select.
SERVER_NAME = "child-product-producer"
#: The class and lane the door serves (the fixture child product).
PRODUCT_CLASS = "fixture.child-product"
PRODUCT_VERSION = "1.0.0"
#: The fixed development bearer token (D-26 `FileTokenSource`), the shipped
#: `mcp_egress_child.py` posture. A test value; never a deployment's.
DEV_TOKEN = "dev-token-child-product-producer"
