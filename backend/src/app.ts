// src/app.ts
import express from "express";
import cors from "cors";
import taskRoutes from "./api/taskRoutes.js";
import minerRoutes from "./api/minerRoutes.js";
import aggregatorRoutes from "./api/aggregatorRoutes.js";
import rewardRoutes from "./api/rewardRoutes.js";
import verificationRoutes from "./api/verificationRoutes.js";
import { AppError } from "./utils/errors.js";

export const app = express();

// CORS configuration - allow frontend on port 3001
app.use(
  cors({
    origin: ["http://localhost:3001", "http://localhost:3000"],
    credentials: true,
  })
);

app.use(express.json({ limit: "50mb" }));
app.use(express.urlencoded({ limit: "50mb", extended: true }));

// Routes
app.use("/tasks", taskRoutes);
app.use("/miners", minerRoutes);
app.use("/aggregator", aggregatorRoutes);
app.use("/rewards", rewardRoutes);
app.use("/verification", verificationRoutes);

// Basic error handler
app.use(
  (
    err: any,
    _req: express.Request,
    res: express.Response,
    _next: express.NextFunction
  ) => {
    if (err instanceof AppError) {
      return res.status(err.statusCode).json({ error: err.message });
    }

    // Log full error for debugging
    console.error("Error details:", {
      message: err?.message,
      stack: err?.stack,
      name: err?.name,
      code: err?.code
    });

    // Return more detailed error in development
    const isDevelopment = process.env.NODE_ENV !== 'production';
    return res.status(500).json({
      error: "Internal server error",
      ...(isDevelopment && {
        details: err?.message,
        type: err?.name
      })
    });
  }
);