import {
  DmPolicySchema,
  GroupPolicySchema,
  MarkdownConfigSchema,
  ReplyRuntimeConfigSchemaShape,
  ToolPolicySchema,
  requireOpenAllowFrom,
} from "openclaw/plugin-sdk";
import { z } from "zod";

const MeshtasticGroupSchema = z
  .object({
    requireMention: z.boolean().optional(),
    tools: ToolPolicySchema,
    toolsBySender: z.record(z.string(), ToolPolicySchema).optional(),
    skills: z.array(z.string()).optional(),
    enabled: z.boolean().optional(),
    allowFrom: z.array(z.string()).optional(),
    systemPrompt: z.string().optional(),
  })
  .strict();

const MeshtasticMqttSchema = z
  .object({
    broker: z.string().optional().default("mqtt.meshtastic.org"),
    port: z.number().int().min(1).max(65535).optional().default(1883),
    username: z.string().optional().default("meshdev"),
    password: z.string().optional().default("large4cats"),
    topic: z.string().optional().default("msh/US/2/json/#"),
    publishTopic: z.string().optional(),
    tls: z.boolean().optional().default(false),
    myNodeId: z.string().optional(),
  })
  .strict();

const MeshtasticTransportSchema = z.enum(["serial", "http", "mqtt"]).optional().default("serial");

const MeshtasticRegionSchema = z
  .enum([
    "UNSET",
    "US",
    "EU_433",
    "EU_868",
    "CN",
    "JP",
    "ANZ",
    "KR",
    "TW",
    "RU",
    "IN",
    "NZ_865",
    "TH",
    "UA_433",
    "UA_868",
    "MY_433",
    "MY_919",
    "SG_923",
    "LORA_24",
  ])
  .optional();

export const MeshtasticAccountSchemaBase = z
  .object({
    name: z.string().optional(),
    enabled: z.boolean().optional(),
    transport: MeshtasticTransportSchema,
    region: MeshtasticRegionSchema,
    nodeName: z.string().optional(),
    serialPort: z.string().optional(),
    httpAddress: z.string().optional(),
    httpTls: z.boolean().optional(),
    mqtt: MeshtasticMqttSchema.optional(),
    dmPolicy: DmPolicySchema.optional().default("pairing"),
    allowFrom: z.array(z.string()).optional(),
    defaultTo: z.string().optional(),
    groupPolicy: GroupPolicySchema.optional().default("disabled"),
    groupAllowFrom: z.array(z.string()).optional(),
    channels: z.record(z.string(), MeshtasticGroupSchema.optional()).optional(),
    mentionPatterns: z.array(z.string()).optional(),
    markdown: MarkdownConfigSchema,
    textChunkLimit: z.number().int().min(50).max(500).optional(),
    ...ReplyRuntimeConfigSchemaShape,
  })
  .strict();

/** Validates transport+connection coherence and open policy allowFrom. */
function validateTransportConnection(value: z.output<typeof MeshtasticAccountSchemaBase>, ctx: z.RefinementCtx) {
  const transport = value.transport ?? "serial";
  if (transport === "serial" && !value.serialPort) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["serialPort"],
      message: 'transport="serial" requires serialPort (e.g. "/dev/ttyUSB0" or "/dev/tty.usbmodem*")',
    });
  }
  if (transport === "http" && !value.httpAddress) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["httpAddress"],
      message: 'transport="http" requires httpAddress (e.g. "meshtastic.local" or "192.168.1.100")',
    });
  }
  if (transport === "mqtt" && !value.mqtt?.broker) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["mqtt", "broker"],
      message: 'transport="mqtt" requires mqtt.broker (e.g. "mqtt.meshtastic.org")',
    });
  }
}

export const MeshtasticAccountSchema = MeshtasticAccountSchemaBase.superRefine((value, ctx) => {
  validateTransportConnection(value, ctx);
  requireOpenAllowFrom({
    policy: value.dmPolicy,
    allowFrom: value.allowFrom,
    ctx,
    path: ["allowFrom"],
    message:
      'channels.meshtastic.dmPolicy="open" requires channels.meshtastic.allowFrom to include "*"',
  });
});

export const MeshtasticConfigSchema = MeshtasticAccountSchemaBase.extend({
  accounts: z.record(z.string(), MeshtasticAccountSchema.optional()).optional(),
}).superRefine((value, ctx) => {
  validateTransportConnection(value, ctx);
  requireOpenAllowFrom({
    policy: value.dmPolicy,
    allowFrom: value.allowFrom,
    ctx,
    path: ["allowFrom"],
    message:
      'channels.meshtastic.dmPolicy="open" requires channels.meshtastic.allowFrom to include "*"',
  });
});
