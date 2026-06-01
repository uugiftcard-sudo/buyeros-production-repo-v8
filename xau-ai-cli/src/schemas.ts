import { z } from "zod";

export const BiasTypeSchema = z.enum(["up", "down", "wait"]);
export type BiasType = z.infer<typeof BiasTypeSchema>;

export const OutputFormatSchema = z.enum(["text", "json"]);
export type OutputFormat = z.infer<typeof OutputFormatSchema>;

export const ModeSchema = z.enum(["direct", "server"]);
export type Mode = z.infer<typeof ModeSchema>;

export const ProviderSchema = z.enum(["openai", "anthropic"]);
export type Provider = z.infer<typeof ProviderSchema>;

export const ScriptRequestSchema = z.object({
  biasType: BiasTypeSchema,
  momentum: z.number().min(0).max(100).optional(),
  position: z.number().min(0).max(100).optional(),
  risk: z.number().min(0).max(100).optional(),
  support: z.string().optional(),
  resistance: z.string().optional(),
  frame: z.string().optional(),
  forceRefresh: z.boolean().optional(),
  topic: z.string().optional(),
  cta: z.string().optional(),
  productName: z.string().optional(),
  accountStyle: z.string().optional(),
});

export type ScriptRequest = z.infer<typeof ScriptRequestSchema>;
