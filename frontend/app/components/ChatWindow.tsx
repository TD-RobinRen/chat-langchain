"use client";

import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { RemoteRunnable } from "@langchain/core/runnables/remote";
import { applyPatch } from "@langchain/core/utils/json_patch";
import useFetchFlowDefinitions from "../utils/useFetchFlowDefinitions"
import useFetchSteps from "../utils/useFetchSteps"
import { EmptyState } from "./EmptyState";
import { ChatMessageBubble, Message } from "./ChatMessageBubble";
import { PopupTextarea } from "./PopupTextarea";
import { marked } from "marked";
import { Renderer } from "marked";
import hljs from "highlight.js";
import "highlight.js/styles/gradient-dark.css";
import "react-toastify/dist/ReactToastify.css";
import {
  IconButton,
  InputGroup,
  InputRightElement,
  Spinner,
} from "@chakra-ui/react";
import { ArrowUpIcon } from "@chakra-ui/icons";
import { apiBaseUrl } from "../utils/constants";
import { diff } from "json-diff";
import { matchCommands, extractJson } from "../utils";

const MODEL_TYPES = ["openai_gpt"];

const defaultLlmValue =
  MODEL_TYPES[Math.floor(Math.random() * MODEL_TYPES.length)];

export const ChatWindow = React.memo(function ChatWindow(props: { conversationId: string }) {
  const conversationId = props.conversationId;
  const fetchFlowDefinitions = useFetchFlowDefinitions();
  const fetchSteps = useFetchSteps();
  const searchParams = useSearchParams();

  const messageContainerRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<Array<Message>>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [llm, setLlm] = useState(searchParams.get("llm") ?? "openai_gpt");
  const initialStepId = searchParams.get("initial_step_id");
  const initialMessage = searchParams.get("initial_message") ?? "";
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  useEffect(() => {
    setLlm(searchParams.get("llm") ?? defaultLlmValue);
    initialMessage !== "undefined" && chatHistory.length === 0 && sendInitialQuestion(initialMessage);
  }, []);

  useEffect(() => {
    if (document.activeElement !== inputRef.current) {
      inputRef.current?.focus();
    }
  },[input])

  const [chatHistory, setChatHistory] = useState<
    { human: string; ai: string }[]
  >([]);
  const sendMessage = async (message?: string) => {
    console.log('sendMessage', message);
    if (messageContainerRef.current) {
      messageContainerRef.current.classList.add("grow");
    }
    if (isLoading) {
      return;
    }
    const messageValue = message ?? input;
    if (messageValue === "") return;
    setInput("");
    setMessages((prevMessages) => [
      ...prevMessages,
      { id: Math.random().toString(), content: messageValue, role: "user" },
    ]);
    setIsLoading(true);

    let accumulatedMessage = "";
    let runId: string | undefined = undefined;
    let messageIndex: number | null = null;

    let renderer = new Renderer();
    renderer.paragraph = (text) => {
      return text + "\n";
    };
    renderer.list = (text) => {
      return `${text}\n\n`;
    };
    renderer.listitem = (text) => {
      return `\n• ${text}`;
    };
    renderer.code = (code, language) => {
      const validLanguage = hljs.getLanguage(language || "")
        ? language
        : "plaintext";
      const highlightedCode = hljs.highlight(
        validLanguage || "plaintext",
        code,
      ).value;
      return `<pre class="highlight bg-gray-700" style="padding: 5px; border-radius: 5px; overflow: auto; overflow-wrap: anywhere; white-space: pre-wrap; max-width: 100%; display: block; line-height: 1.2"><code class="${language}" style="color: #d6e2ef; font-size: 12px; ">${highlightedCode}</code></pre>`;
    };
    marked.setOptions({ renderer });

    try {
      const sourceStepName = "";
      let streamedResponse: Record<string, any> = {};
      const remoteChain = new RemoteRunnable({
        url: apiBaseUrl + "/chat",
        options: {
          timeout: 600000,
        },
      });
      const llmDisplayName = llm ?? "openai_gpt";
      let diffJson = undefined;
      // /diff 3fe9ba57da1b41e8a094e08afa5025f5, 4ca93fc076f84d56bc43114fcede44a2
      const messageType = matchCommands(messageValue)?.split(' ')[0].substring(1) ?? 'chat'
      let stepsChange = undefined
      let requestPrams: any = {
        chat_type: messageType
      };

      switch(messageType) {
        case 'diff': {
          const ids:Array<string> = messageValue.substring(messageValue.indexOf(' ') + 1).replace(/\s/g, '').split(',');
          console.log('ids', ids);
          const baseFlow = await fetchFlowDefinitions(ids[0]); 
          const baseFlowSteps = await fetchSteps(ids[0]);
          baseFlow.steps = baseFlowSteps._embedded.steps

          const referenceFlow = await fetchFlowDefinitions(ids[1]); 
          const referenceFlowSteps = await fetchSteps(ids[1]);
          referenceFlow.steps = referenceFlowSteps._embedded.steps
          console.log('baseFlow', baseFlow);
          console.log('referenceFlow', referenceFlow);
          
          diffJson = diff(baseFlow, referenceFlow, {
            full: true,
            // outputKeys: ["created_at"],
            // excludeKeys: [
            //   "id",
            //   "account_id",
            //   "user_id",
            //   "name",
            //   "description",
            //   "trigger_type",
            //   "status",
            //   "version",
            //   "previous_version",
            //   "next_version",
            //   "created_at",
            //   "updated_at",
            //   "valid",
            //   "validation_status",
            //   "initial_step_id",
            //   "group_id",
            //   "pre_conditions",
            // ]
          });
        
          console.log('diffJson', diffJson);
          console.log('messageType', messageType);

          stepsChange = diffJson.steps.map((v: any) => v[1].component.name)
          stepsChange = Array.from(new Set(stepsChange));
          console.log('stepsChange', stepsChange);
          requestPrams = { ...requestPrams,
            question: messageValue,
            chat_history: chatHistory,
            diff_json: diffJson,
            component_list: stepsChange
          }
          break;
        }
        case 'explain': {
          requestPrams = { ...requestPrams,
            question: messageValue,
            chat_history: chatHistory,
            flow_json: {},
            component_list: stepsChange
          }
          break;
        }
        case 'generate': {
          requestPrams = { ...requestPrams,
            question: messageValue,
            chat_history: chatHistory,
          }
          break;
        }
        default: {
          requestPrams = { ...requestPrams,
            question: messageValue,
            chat_history: chatHistory,
            flow_json: {},
          }
          break;
        }
      }
      if (matchCommands(messageValue) === '/diff') {
      }
      const streamLog = await remoteChain.streamLog(
        requestPrams,
        {
          configurable: {
            llm: llmDisplayName,
          },
          tags: ["model:" + llmDisplayName],
          metadata: {
            conversation_id: conversationId,
            llm: llmDisplayName,
          },
        },
        {
          includeNames: [sourceStepName],
        },
      );

      for await (const chunk of streamLog) {
        streamedResponse = applyPatch(streamedResponse, chunk.ops).newDocument;
        if (streamedResponse.id !== undefined) {
          runId = streamedResponse.id;
        }
        if (Array.isArray(streamedResponse?.streamed_output)) {
          console.log('streamedResponse', streamedResponse?.streamed_output);
          accumulatedMessage = streamedResponse?.streamed_output.map((output) => {
            console.log('item', output);
            console.log('item.content', output?.content);
            console.log('item.kwargs.content', output?.kwargs?.content);
            console.log('item.lc_kwargs.content', output?.lc_kwargs?.content);
            
            const flowJson = extractJson(output);

            if (flowJson) {
              let rawContent: any = null;
              rawContent = JSON.parse(flowJson[1]);

              if (initialStepId) {
                rawContent.initial_step_id = initialStepId;
                rawContent.steps[0].id = initialStepId;
              }
              window.rawContent = rawContent;
              return output
            } else {
              window.rawContent = null;
              return output?.content || "";
            } 
          }).join("");
        }
        const parsedResult = marked.parse(accumulatedMessage);
        
        setMessages((prevMessages) => {
          let newMessages = [...prevMessages];
          if (
            messageIndex === null ||
            newMessages[messageIndex] === undefined
          ) {
            messageIndex = newMessages.length;

            newMessages.push({
              id: Math.random().toString(),
              content: parsedResult,
              runId: runId,
              role: "assistant",
              // rawContent: rawContent,
            });
          } else if (newMessages[messageIndex] !== undefined) {
            newMessages[messageIndex].content = parsedResult;
            newMessages[messageIndex].runId = runId;
          }
          return newMessages;
        });
      }

      setChatHistory((prevChatHistory) => [
        ...prevChatHistory,
        { human: messageValue, ai: accumulatedMessage },
      ]);
    } catch (e) {
      setMessages((prevMessages) => prevMessages.slice(0, -1));
      setInput(messageValue);
      throw e;
    } finally {
      setIsLoading(false);
    }
  };

  const sendInitialQuestion = async (question: string) => {
    await sendMessage(question);
  };

  return (
    <div className="flex flex-col items-center p-8 rounded grow max-h-full">
      <div
        className="flex flex-col-reverse w-full mb-2 overflow-auto flex-1"
        ref={messageContainerRef}
      >
        {messages.length > 0 ? (
          [...messages]
            .reverse()
            .map((m, index) => (
              <ChatMessageBubble
                key={m.id}
                message={{ ...m }}
                aiEmoji="🦜"
                isMostRecent={index === 0}
                messageCompleted={!isLoading}
              ></ChatMessageBubble>
            ))
        ) : (
          <EmptyState onChoice={sendInitialQuestion} />
        )}
      </div>
      <InputGroup size="md" alignItems={"center"}>
        <PopupTextarea
          value={input}
          ref={inputRef}
          onChange={value => setInput(value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              console.log("Enter key pressed", input)
              e.preventDefault();
              sendMessage();
            } else if (e.key === "Enter" && e.shiftKey) {
              e.preventDefault();
              setInput(input + "\n");
            } 
          }}
        />
        <InputRightElement h="full">
          <IconButton
            colorScheme="blue"
            rounded={"full"}
            aria-label="Send"
            icon={isLoading ? <Spinner /> : <ArrowUpIcon />}
            type="submit"
            onClick={(e) => {
              e.preventDefault();
              sendMessage();
            }}
          />
        </InputRightElement>
      </InputGroup>
    </div>
  );
});
