import { toast } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";
import { emojisplosion } from "emojisplosion";
import { useState, useRef } from "react";
import * as DOMPurify from "dompurify";
import {
  VStack,
  Flex,
  Heading,
  Text,
  HStack,
  Box,
  Button,
  Divider,
  Spacer,
} from "@chakra-ui/react";
import { sendFeedback } from "../utils/sendFeedback";
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
  const [isLoading, setIsLoading] = useState(false);
  const [traceIsLoading, setTraceIsLoading] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [comment, setComment] = useState("");
  const [feedbackColor, setFeedbackColor] = useState("");
  const upButtonRef = useRef(null);
  const downButtonRef = useRef(null);

  const cumulativeOffset = function (element: HTMLElement | null) {
    var top = 0,
      left = 0;
    do {
      top += element?.offsetTop || 0;
      left += element?.offsetLeft || 0;
      element = (element?.offsetParent as HTMLElement) || null;
    } while (element);

    return {
      top: top,
      left: left,
    };
  };

  const sendUserFeedback = async (score: number, key: string) => {
    let run_id = runId;
    if (run_id === undefined) {
      return;
    }
    if (isLoading) {
      return;
    }
    setIsLoading(true);
    try {
      const data = await sendFeedback({
        score,
        runId: run_id,
        key,
        feedbackId: feedback?.feedback_id,
        comment,
        isExplicit: true,
      });
      if (data.code === 200) {
        setFeedback({ run_id, score, key, feedback_id: data.feedbackId });
        score == 1 ? animateButton("upButton") : animateButton("downButton");
        if (comment) {
          setComment("");
        }
      }
    } catch (e: any) {
      console.error("Error:", e);
      toast.error(e.message);
    }
    setIsLoading(false);
  };
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

  const animateButton = (buttonId: string) => {
    let button: HTMLButtonElement | null;
    if (buttonId === "upButton") {
      button = upButtonRef.current;
    } else if (buttonId === "downButton") {
      button = downButtonRef.current;
    } else {
      return;
    }
    if (!button) return;
    let resolvedButton = button as HTMLButtonElement;
    resolvedButton.classList.add("animate-ping");
    setTimeout(() => {
      resolvedButton.classList.remove("animate-ping");
    }, 500);

    emojisplosion({
      emojiCount: 10,
      uniqueness: 1,
      position() {
        const offset = cumulativeOffset(button);

        return {
          x: offset.left + resolvedButton.clientWidth / 2,
          y: offset.top + resolvedButton.clientHeight / 2,
        };
      },
      emojis: buttonId === "upButton" ? ["👍"] : ["👎"],
    });
  };

  return (
    <VStack align="start"
      spacing={5} 
      px={5} 
      py={2}
      scrollPaddingY={14} 
      backgroundColor={ isUser ? "gray.50" : "purple.50" }
      borderRadius={8}
      mb={4}
      maxW="85%"
      ml={ isUser ? "auto" : undefined }
    >
      {!isUser && (
        <Text fontWeight="medium" color="blue.300">
          Answer
        </Text>
      )}

      {isUser ? (
        <Text fontWeight="medium">
          {content}
        </Text>
      ) : (
        <Box className="whitespace-pre-wrap">
          {answerElements}
        </Box>
      )}

      {props.message.role !== "user" &&
        props.isMostRecent &&
        props.messageCompleted && (
          <HStack spacing={2}>
            <Button
              ref={upButtonRef}
              size="sm"
              variant="outline"
              colorScheme={feedback === null ? "green" : "gray"}
              onClick={() => {
                if (feedback === null && props.message.runId) {
                  sendUserFeedback(1, "user_score");
                  animateButton("upButton");
                  setFeedbackColor("border-4 border-green-300");
                } else {
                  toast.error("You have already provided your feedback.");
                }
              }}
            >
              👍
            </Button>
            <Button
              ref={downButtonRef}
              size="sm"
              variant="outline"
              colorScheme={feedback === null ? "red" : "gray"}
              onClick={() => {
                if (feedback === null && props.message.runId) {
                  sendUserFeedback(0, "user_score");
                  animateButton("downButton");
                  setFeedbackColor("border-4 border-red-300");
                } else {
                  toast.error("You have already provided your feedback.");
                }
              }}
            >
              👎
            </Button>
            <Spacer />
            <Button
              size="sm"
              variant="outline"
              colorScheme={runId === null ? "blue" : "gray"}
              onClick={(e) => {
                e.preventDefault();
                viewTrace();
              }}
              isLoading={traceIsLoading}
              loadingText="🔄"
              color="gray"
            >
              🦜🛠️ View trace
            </Button>
          </HStack>
        )}

      {!isUser && <Divider mt={4} mb={4} />}
    </VStack>
  );
}
