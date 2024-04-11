import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { useState } from "react";
import * as DOMPurify from "dompurify";
import {
  VStack,
  Flex,
  Heading,
  HStack,
  Box,
  Button,
  Divider,
} from "@chakra-ui/react";
import { apiBaseUrl } from "../utils/constants";

export type Message = {
  id: string;
  createdAt?: Date;
  content: string;
  role: "system" | "user" | "assistant" | "function";
  runId?: string;
  name?: string;
  function_call?: { name: string };
};
export type Feedback = {
  feedback_id: string;
  run_id: string;
  key: string;
  score: number;
  comment?: string;
};

const createAnswerElements = (
  content: string,
) => {
  const elements: JSX.Element[] = [];
  let prevIndex = 0;
  elements.push(
    <span
      key={`content:${prevIndex}`}
      dangerouslySetInnerHTML={{
        __html: DOMPurify.sanitize(content.slice(prevIndex)),
      }}
    ></span>,
  );
  return elements;
};

export function ChatMessageBubble(props: {
  message: Message;
  aiEmoji?: string;
  isMostRecent: boolean;
  messageCompleted: boolean;
}) {
  const { role, content, runId } = props.message;
  const isUser = role === "user";
  const [traceIsLoading, setTraceIsLoading] = useState(false);

  const viewTrace = async () => {
    try {
      setTraceIsLoading(true);
      const response = await fetch(apiBaseUrl + "/get_trace", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          run_id: runId,
        }),
      });

      const data = await response.json();

      if (data.code === 400) {
        toast.error("Unable to view trace");
        throw new Error("Unable to view trace");
      } else {
        const url = data.replace(/['"]+/g, "");
        window.open(url, "_blank");
        setTraceIsLoading(false);
      }
    } catch (e: any) {
      console.error("Error:", e);
      setTraceIsLoading(false);
      toast.error(e.message);
    }
  };

  const answerElements =
    role === "assistant"
      ? createAnswerElements(
          content
        )
      : [];

  return (
    <VStack align="start" spacing={5} pb={5}>
      {!isUser && (
        <>
          <Heading size="lg" fontWeight="medium" color="blue.300">
            Answer
          </Heading>
        </>
      )}

      {isUser ? (
        <Heading size="lg" fontWeight="medium" color="white">
          {content}
        </Heading>
      ) : (
        <Box className="whitespace-pre-wrap" color="white">
          {answerElements}
        </Box>
      )}

      {props.message.role !== "user" &&
        props.isMostRecent &&
        props.messageCompleted && (
          <HStack spacing={2}>
            <Button
              size="sm"
              variant="outline"
              colorScheme={runId === null ? "blue" : "gray"}
              onClick={(e) => {
                e.preventDefault();
              }}
              isLoading={traceIsLoading}
              loadingText="🔄"
              color="white"
            >
              🛠️ Apply
            </Button>
          </HStack>
        )}

      {!isUser && <Divider mt={4} mb={4} />}
    </VStack>
  );
}
