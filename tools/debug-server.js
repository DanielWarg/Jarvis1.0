#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new Server(
  { name: "debug-tools", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.tool(
  "echo",
  "Echo back the given text",
  z.object({ message: z.string() }),
  async ({ message }) => {
    return { content: [{ type: "text", text: message }] };
  }
);

server.tool(
  "log",
  "Log a message to the console",
  z.object({
    level: z.enum(["info", "warn", "error"]).default("info"),
    message: z.string()
  }),
  async ({ level, message }) => {
    const logger = console[level] || console.log;
    logger(message);
    return { content: [{ type: "text", text: `Logged ${level}: ${message}` }] };
  }
);

const transport = new StdioServerTransport();
await server.connect(transport);
