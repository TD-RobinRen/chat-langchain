import useRequest from "./useRequest";
import { apiHost } from "./constants";

const useFetchInteractionTriggers = () => {
    const { get } = useRequest()
    const fetchInteractionTriggers = (flowId:string) => get(`https://${apiHost}/flow_definitions/${flowId}/interaction_triggers`, null);
  
    return fetchInteractionTriggers;
  };

export default useFetchInteractionTriggers;
