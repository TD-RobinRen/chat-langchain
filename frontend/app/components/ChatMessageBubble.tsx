import "react-toastify/dist/ReactToastify.css";
import { useState } from "react";
import * as DOMPurify from "dompurify";
import {
  VStack,
  Text,
  HStack,
  Box,
  Button,
} from "@chakra-ui/react";

export type Message = {
  id: string;
  createdAt?: Date;
  content: string;
  role: "system" | "user" | "assistant" | "function";
  runId?: string;
  name?: string;
  function_call?: { name: string };
  rawContent?: {
    steps: any;
  };
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
  const [applyIsLoading, setApplyIsLoading] = useState(false);

  const createSteps = async () => {
  const urlParams = new URLSearchParams(window.location.search);
  const flowId = urlParams.get('flow_id');
  const auth_token = { authorization: urlParams.get('auth_token')??'', 'Content-Type': 'application/json' };
  const apiHost = "api.talkdeskstg.com";
    
  setApplyIsLoading(true);
  try {
    console.log('3     body', JSON.stringify(window.rawContent?.steps))
    const response = await fetch(`https://${apiHost}/flow_definitions/${flowId}/steps`, {
      method: 'PUT',
      headers: auth_token,
      body: JSON.stringify(window.rawContent?.steps)
    });
  
    if (response.status === 200) {
      window.parent.postMessage('refresh', 'http://localhost:8000/');
      setApplyIsLoading(false);
      return await response.json();
    }
    return {};
  } catch (e: any) {
    setApplyIsLoading(false);
    throw new Error(`Error occurs: ${e}`);
  }
};

  const answerElements =
    role === "assistant"
      ? createAnswerElements(
          content
        )
      : [];

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
          {content.split('\n').map((line, index) => (
            <div key={index}>
              {line}
              <br />
            </div>
          ))}
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
              size="sm"
              variant="outline"
              colorScheme={runId === null ? "blue" : "gray"}
              onClick={(e) => {
                e.preventDefault();
                createSteps();
              }}
              isLoading={applyIsLoading}
              loadingText="🔄"
              color="gray"
            >
              🛠️ Apply
            </Button>
          </HStack>
        )}
    </VStack>
  );
}