import type { Metadata } from "next";
import { AssistantChat } from "@/components/assistant/assistant-chat";

export const metadata: Metadata = { title: "Assistant · Wallet Agent" };

export default function Assistant() {
  return <AssistantChat />;
}
