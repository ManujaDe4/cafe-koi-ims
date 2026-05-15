import Fastify from "fastify";
import cors from "@fastify/cors";
import { PrismaClient } from "@prisma/client";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const prisma = new PrismaClient();

const app = Fastify({
  logger: {
    level: process.env.NODE_ENV === "production" ? "warn" : "info",
  },
});

// ─── Plugins ────────────────────────────────────────────────────────────────
await app.register(cors, {
  origin: [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
  ],
});

// ─── Health ─────────────────────────────────────────────────────────────────
app.get("/health", async () => ({ status: "ok", service: "backend-pos" }));

// ─── Products ───────────────────────────────────────────────────────────────
app.get("/api/products", async () => {
  return prisma.product.findMany({
    where: { available: true },
    orderBy: { name: "asc" },
  });
});

app.get("/api/products/:id", async (request, reply) => {
  const product = await prisma.product.findUnique({
    where: { id: Number(request.params.id) },
  });
  if (!product) return reply.status(404).send({ error: "Product not found" });
  return product;
});

app.post("/api/products", async (request, reply) => {
  const product = await prisma.product.create({ data: request.body });
  return reply.status(201).send(product);
});

// ─── Orders ─────────────────────────────────────────────────────────────────
app.get("/api/orders", async () => {
  return prisma.order.findMany({
    include: { items: { include: { product: true } } },
    orderBy: { createdAt: "desc" },
  });
});

app.get("/api/orders/:id", async (request, reply) => {
  const order = await prisma.order.findUnique({
    where: { id: Number(request.params.id) },
    include: { items: { include: { product: true } } },
  });
  if (!order) return reply.status(404).send({ error: "Order not found" });
  return order;
});

app.post("/api/orders", async (request, reply) => {
  const { items, customerName, notes } = request.body;

  const order = await prisma.$transaction(async (tx) => {
    let totalAmount = 0;

    const resolvedItems = await Promise.all(
      items.map(async ({ productId, quantity }) => {
        const product = await tx.product.findUniqueOrThrow({
          where: { id: productId },
        });
        const subtotal = parseFloat(product.price) * quantity;
        totalAmount += subtotal;
        return {
          productId,
          quantity,
          unitPrice: product.price,
          subtotal: subtotal.toFixed(2),
        };
      })
    );

    const count = await tx.order.count();
    const orderNumber = `KOI-${String(count + 1).padStart(4, "0")}`;

    return tx.order.create({
      data: {
        orderNumber,
        customerName,
        notes,
        totalAmount: totalAmount.toFixed(2),
        items: { create: resolvedItems },
      },
      include: { items: true },
    });
  });

  return reply.status(201).send(order);
});

app.patch("/api/orders/:id/status", async (request, reply) => {
  const order = await prisma.order.update({
    where: { id: Number(request.params.id) },
    data: { status: request.body.status },
  });
  return order;
});

// ─── Graceful Shutdown ───────────────────────────────────────────────────────
const gracefulShutdown = async (signal) => {
  app.log.info(`Received ${signal}, shutting down…`);
  await app.close();
  await prisma.$disconnect();
  process.exit(0);
};

process.on("SIGTERM", () => gracefulShutdown("SIGTERM"));
process.on("SIGINT",  () => gracefulShutdown("SIGINT"));

// ─── Start ───────────────────────────────────────────────────────────────────
const PORT = parseInt(process.env.PORT ?? "3000", 10);

try {
  await app.listen({ port: PORT, host: "0.0.0.0" });
} catch (err) {
  app.log.error(err);
  await prisma.$disconnect();
  process.exit(1);
}
