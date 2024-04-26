import useRequest from "./useRequest";
import { apiHost } from "./constants";

const useFetchFlowDefinitions = () => {
    const { get } = useRequest()
    const fetchFlowDefinitions = (flowId:string) => get(`https://${apiHost}/flow_definitions/${flowId}`, null);
  
    return fetchFlowDefinitions;
  };

export default useFetchFlowDefinitions;
