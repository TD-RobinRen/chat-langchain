import { apiBaseUrl } from "../utils/constants";
import { RemoteRunnable } from "@langchain/core/runnables/remote";
import { applyPatch } from "@langchain/core/utils/json_patch";
import { extractJson, matchCommands } from "../utils";
import { useState } from "react";
import { diff } from "json-diff";
import useFetchFlowDefinitions from "../utils/useFetchFlowDefinitions"
import useFetchSteps from "../utils/useFetchSteps"
import { useSearchParams } from "next/navigation";

const model = "openai_gpt"

type Question = {
  question: string,
  chat_history: Array<any>,
  diff_json?: object,
  chat_type: string,
  flow_json?: object,
  component_list: Array<any>
};

const useSendMessage = () => {
  const [accumulatedMessage, setAccumulatedMessage] = useState('');
  const [rawContent, setRawContent] = useState({});
  const fetchFlowDefinitions = useFetchFlowDefinitions();
  const fetchSteps = useFetchSteps();
  const searchParams = useSearchParams();
  const urlParams = new URLSearchParams(window.location.search);
  const initialStepId = urlParams.get("initial_step_id");
  const flowId = searchParams.get("flow_id") ?? "";
  
  const remoteChain = new RemoteRunnable({
    url: apiBaseUrl + "/chat",
    options: {
      timeout: 600000,
    },
  });
  const fetchFlowAndSteps = async (flowId: string) => {
    const flow = await fetchFlowDefinitions(flowId); 
    const flowSteps = await fetchSteps(flowId);
    flow.steps = flowSteps._embedded.steps;
    return flow;
  }

  const getRequestPrams = async (messageValue: string, chatHistory: { human: string; ai: string }[]) => {
    const messageType = matchCommands(messageValue)?.split(' ')[0].substring(1) ?? 'chat'
      let stepsChange = undefined
      let requestPrams: any = {
        chat_type: messageType
      };

    switch(messageType) {
      case 'diff': {
        const ids:Array<string> = messageValue.substring(messageValue.indexOf(' ') + 1).replace(/\s/g, '').split(',');
        console.log('ids', ids);
        const baseFlow = await fetchFlowAndSteps(ids[0]);

        const referenceFlow = await fetchFlowAndSteps(ids[1]);
        console.log('baseFlow', baseFlow);
        console.log('referenceFlow', referenceFlow);
        
        const diffJson = diff(baseFlow, referenceFlow, {
          full: true,
          excludeKeys: [
            "id",
            "account_id",
            "user_id",
            "description",
            "trigger_type",
            "status",
            "previous_version",
            "next_version",
            "created_at",
            "updated_at",
            "valid",
            "validation_status",
            "group_id",
            "pre_conditions",
          ]
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
      default: {
        const flow = await fetchFlowAndSteps(flowId);

        stepsChange = flow?.steps?.map((v: any) => v[1].component.name)
        stepsChange = Array.from(new Set(stepsChange));

        requestPrams = { ...requestPrams,
          question: messageValue,
          chat_history: chatHistory,
          flow_json: flow,
          component_list: stepsChange
        }
        break;
      }
    }
    return requestPrams
  }

  const sendMessage = async(message: string, conversationId: string, chatHistory: { human: string; ai: string }[]) => {
    let streamedResponse: Record<string, any> = {};
    let runId: string | undefined = undefined;
    let streamedOutput = "";

    const configuration =  {
      configurable: {
        llm: model,
      },
      tags: ["model:" + model],
      metadata: {
        conversation_id: conversationId,
        llm: model,
      },
    }

    const includeNames= {
      includeNames: [""],
    }

    
    // let accumulatedMessage = "";
    // let rawContent: any = null;

    const streamLog = await remoteChain.streamLog(
      getRequestPrams(message, chatHistory),
      configuration,
      includeNames,
    );

    for await (const chunk of streamLog) {
      streamedResponse = applyPatch(streamedResponse, chunk.ops).newDocument;
      if (streamedResponse.id !== undefined) {
        runId = streamedResponse.id;
      }
      if (Array.isArray(streamedResponse?.streamed_output)) {
        console.log('streamedResponse', streamedResponse?.streamed_output);
        streamedOutput = streamedResponse?.streamed_output.map((output) => {
          console.log('item', output);
          console.log('item.content', output?.content);
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

      setAccumulatedMessage(streamedOutput);
      setRawContent(rawContent);
      // const parsedResult = marked.parse(accumulatedMessage);
    };
  };

  return {
    accumulatedMessage,
    rawContent,
    sendMessage,
  };
}

export default useSendMessage;