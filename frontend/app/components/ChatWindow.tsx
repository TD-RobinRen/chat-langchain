"use client";

import React, { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { RemoteRunnable } from "@langchain/core/runnables/remote";
import { applyPatch } from "@langchain/core/utils/json_patch";

import { EmptyState } from "./EmptyState";
import { ChatMessageBubble, Message } from "./ChatMessageBubble";
import { AutoResizeTextarea } from "./AutoResizeTextarea";
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
import { Select, Link } from "@chakra-ui/react";
import { apiBaseUrl } from "../utils/constants";

const MODEL_TYPES = [
  "openai_gpt",
];

const defaultLlmValue =
  MODEL_TYPES[Math.floor(Math.random() * MODEL_TYPES.length)];

export function ChatWindow(props: { conversationId: string }) {
  const conversationId = props.conversationId;

  const searchParams = useSearchParams();

  const messageContainerRef = useRef<HTMLDivElement | null>(null);
  const [messages, setMessages] = useState<Array<Message>>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [llm, setLlm] = useState(
    searchParams.get("llm") ?? "openai_gpt",
  );
  const [llmIsLoading, setLlmIsLoading] = useState(true);
  useEffect(() => {
    setLlm(searchParams.get("llm") ?? defaultLlmValue);
    setLlmIsLoading(false);
  }, []);

  const [chatHistory, setChatHistory] = useState<
    { human: string; ai: string }[]
  >([]);

  const sendMessage = async (message?: string) => {
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
      // const sourceStepName = "";
      // let streamedResponse: Record<string, any> = {};
      // const remoteChain = new RemoteRunnable({
      //   url: apiBaseUrl + "/chat",
      //   options: {
      //     timeout: 600000,
      //   },
      // });
      // const llmDisplayName = llm ?? "openai_gpt";
      // const streamLog = await remoteChain.streamLog(
      //   {
      //     question: messageValue,
      //     chat_history: chatHistory,
      //   },
      //   {
      //     configurable: {
      //       llm: llmDisplayName,
      //     },
      //     tags: ["model:" + llmDisplayName],
      //     metadata: {
      //       conversation_id: conversationId,
      //       llm: llmDisplayName,
      //     },
      //   },
      //   {
      //     includeNames: [sourceStepName],
      //   },
      // );
      // for await (const chunk of streamLog) {
      //   streamedResponse = applyPatch(streamedResponse, chunk.ops).newDocument;
      //   if (streamedResponse.id !== undefined) {
      //     runId = streamedResponse.id;
      //   }
      //   if (Array.isArray(streamedResponse?.streamed_output)) {
      //     accumulatedMessage = streamedResponse?.streamed_output.map(output => {
      //       if (typeof output === 'object' && output !== null) {
      //         return '\n\n```json\n' + JSON.stringify(output, null, 2) + '\n````\n\n';
      //       } else {
      //         return output;
      //       }
      //     }).join('');
      //   }
      //   const parsedResult = marked.parse(accumulatedMessage);

      //   setMessages((prevMessages) => {
      //     let newMessages = [...prevMessages];
      //     if (
      //       messageIndex === null ||
      //       newMessages[messageIndex] === undefined
      //     ) {
      //       messageIndex = newMessages.length;
      //       newMessages.push({
      //         id: Math.random().toString(),
      //         content: parsedResult,
      //         runId: runId,
      //         role: "assistant"
      //       });
      //     } else if (newMessages[messageIndex] !== undefined) {
      //       newMessages[messageIndex].content = parsedResult;
      //       newMessages[messageIndex].runId = runId;
      //     }
      //     return newMessages;
      //   });
      // }

      const output = {"id":"f45835f16d2644d89aba76206340f562","account_id":"64643fadae22dd58843ad1ab","user_id":"64649e765e3c241a03c651aa","name":"Enming Test","description":"","trigger_type":"voice_inbound","status":"draft","version":1,"created_at":"2024-03-06T08:14:38.810015Z","updated_at":"2024-04-12T07:34:36.298496Z","valid":true,"validation_status":"valid","initial_step_id":"04fc3ff9-6097-4c11-9363-0bd37c072eba","group_id":"ad3d5243f79d444ab96dde388eb3606e","pre_conditions":{},"steps":[{"id":"04fc3ff9-6097-4c11-9363-0bd37c072eba","name":"Initial step","component":{"name":"inbound_voice-ZjE1ZjM0MG","version":"1.3.x"},"properties":{},"exits":[{"_key":"231bd8d0-927e-4b83-8b4d-503516629463","name":"ok","transition":"a83d1c76-47e4-419e-aa63-819e0cdb34e1"}],"context_mappings":{},"created_at":"2024-03-06T08:19:24.154000Z"},{"id":"a83d1c76-47e4-419e-aa63-819e0cdb34e1","name":"2","component":{"name":"play_audio-NjFkZDU2MG","version":"2.16.x"},"properties":{"audio_message":{"text":"test test gsfsfdsf","language":"en-US"}},"exits":[{"_key":"5e14026d-a54d-48b7-a85c-f6c3056c7a4b","name":"ok","transition":"b74f6bcd-1320-45d4-b9c4-d2c618b1c75e"}],"context_mappings":{},"created_at":"2024-03-11T07:48:16.473000Z","on_error":{"_key":"29a386f1-df44-4641-a107-6790066d9b4e","type":"end_flow","name":"error"}},{"id":"b74f6bcd-1320-45d4-b9c4-d2c618b1c75e","name":"3","component":{"name":"input_ivr-ZDgxODY4Mz","version":"2.8.x"},"properties":{"message":{"text":"123","language":"en-US"},"keypress_inputs":{"num_digits":2,"finish_on_key":"#"}},"exits":[{"_key":"66777d23-0b29-4fee-bda6-db5423685fd6","name":"ok","transition":"f459dac9-3a99-4ff0-9f90-e8f1352b26cf"},{"_key":"035b0fe5-a75e-4410-abd3-c2acba8341d9","name":"timeout","condition":{"timeout":5},"transition":"54980884-064a-456e-83e2-7f9a82daefce"}],"context_mappings":{"1":"digits"},"created_at":"2024-03-11T07:49:09.458000Z"},{"id":"f459dac9-3a99-4ff0-9f90-e8f1352b26cf","name":"4","component":{"name":"voice_ivr-M2JmMTc2YT","version":"2.10.x"},"properties":{"audio_message":{"text":"223"},"timeout_selection":{"speech_timeout":2},"language_selection":{"language":"en-US"}},"exits":[{"_key":"5cdda0b8-34bb-4388-9418-c9a84b794dae","name":"no_match","transition":"55e931d7-0e3f-42e9-a103-b82eb7d64240"},{"_key":"e2b60b8c-d266-47a9-9e2c-6ffa9d48e8c2","name":"timeout","transition":"55e931d7-0e3f-42e9-a103-b82eb7d64240"},{"_key":"f07bca7d-96e2-416a-af0f-5b357b55dcf1","name":"1","condition":{"routing_conditions":{"value":[{"value":"%{current_flow.1}","operation":"contains"}],"operation":"any"}},"transition":"55e931d7-0e3f-42e9-a103-b82eb7d64240"}],"context_mappings":{"input":"speech"},"created_at":"2024-03-11T07:51:55.947000Z","on_error":{"_key":"e5dd1338-0788-4a56-9766-d7f6397901a0","type":"end_flow","name":"error"}},{"id":"54980884-064a-456e-83e2-7f9a82daefce","name":"5","component":{"name":"voicemail-NGQ0ZDE5Nj","version":"2.4.x"},"properties":{"record_parameters":{"without_transcription_max_duration":300},"assignment_parameters":{"ring_groups":{"ring_groups_list":["enming"]}}},"exits":[],"context_mappings":{},"created_at":"2024-03-11T07:52:39.747000Z"},{"id":"55e931d7-0e3f-42e9-a103-b82eb7d64240","name":"6","component":{"name":"hangup_call-OTE5ZmM0NW","version":"1.0.x"},"properties":{},"exits":[],"context_mappings":{},"created_at":"2024-03-11T07:54:16.552000Z"}],"model":{"1":{"display_name":"1","exposed":false,"format":{"type":"string","$schema":"http://json-schema.org/draft-04/schema#","pattern":"^[0-9*#]+$"},"namespace":"current_flow"},"input":{"display_name":"input","exposed":false,"format":{"type":"string","$schema":"http://json-schema.org/draft-04/schema#","pattern":"^[0-9*#]+$"},"namespace":"current_flow"}}}
      accumulatedMessage = marked.parse('\n\n```json\n' + JSON.stringify(output, null, 2) + '\n````\n\n')

      setMessages((prevMessages) => {
        let newMessages = [...prevMessages];
        if (
          messageIndex === null ||
          newMessages[messageIndex] === undefined
        ) {
          messageIndex = newMessages.length;
          newMessages.push({
            id: Math.random().toString(),
            content: accumulatedMessage,
            runId: runId,
            role: "assistant",
            rawContent: output,
          });
        } else if (newMessages[messageIndex] !== undefined) {
          newMessages[messageIndex].content = accumulatedMessage;
          newMessages[messageIndex].runId = runId;
        }
        return newMessages;
      });

      setChatHistory((prevChatHistory) => [
        ...prevChatHistory,
        { human: messageValue, ai: accumulatedMessage },
      ]);
      setIsLoading(false);
    } catch (e) {
      setMessages((prevMessages) => prevMessages.slice(0, -1));
      setIsLoading(false);
      setInput(messageValue);
      throw e;
    }
  };

  const sendInitialQuestion = async (question: string) => {
    await sendMessage(question);
  };

  const insertUrlParam = (key: string, value?: string) => {
    if (window.history.pushState) {
      const searchParams = new URLSearchParams(window.location.search);
      searchParams.set(key, value ?? "");
      const newurl =
        window.location.protocol +
        "//" +
        window.location.host +
        window.location.pathname +
        "?" +
        searchParams.toString();
      window.history.pushState({ path: newurl }, "", newurl);
    }
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
        <AutoResizeTextarea
          value={input}
          maxRows={5}
          marginRight={"56px"}
          placeholder="Input something..."
          borderColor={"rgb(58, 58, 61)"}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
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
}
