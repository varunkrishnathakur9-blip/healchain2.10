import { Request, Response, NextFunction } from "express";

/**
 * Require specific fields to be present in req.body
 */
export function requireFields(fields: string[]) {
  return (req: Request, res: Response, next: NextFunction) => {
    for (const field of fields) {
      if (
        req.body[field] === undefined ||
        req.body[field] === null
      ) {
        return res.status(400).json({
          error: `Missing required field: ${field}`
        });
      }
    }
    next();
  };
}
