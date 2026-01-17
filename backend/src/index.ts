import { app } from "./app.js";
import { env } from "./config/env.js";
import { prisma } from "./config/database.config.js";
import { logger } from "./utils/logger.js";
import { startTaskScheduler, stopTaskScheduler } from "./services/taskScheduler.js";

async function start() {
  try {
    await prisma.$connect();
    logger.info("Database connected");

    // Start task status scheduler
    startTaskScheduler();

    app.listen(env.PORT, () => {
      logger.info(`HealChain backend running on port ${env.PORT}`);
      logger.info(`Environment: ${env.NODE_ENV}`);
    });

    // Graceful shutdown
    process.on("SIGTERM", () => {
      logger.info("SIGTERM received, shutting down gracefully");
      stopTaskScheduler();
      prisma.$disconnect().then(() => {
        process.exit(0);
      });
    });

    process.on("SIGINT", () => {
      logger.info("SIGINT received, shutting down gracefully");
      stopTaskScheduler();
      prisma.$disconnect().then(() => {
        process.exit(0);
      });
    });
  } catch (err: any) {
    logger.error(`Startup failed: ${err.message}`);
    process.exit(1);
  }
}

start();
