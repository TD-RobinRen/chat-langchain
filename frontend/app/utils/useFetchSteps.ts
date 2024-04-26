import useRequest from "./useRequest";
import { apiHost } from "./constants";

const useFetchSteps = () => {
    const { get } = useRequest()
    const fetchSteps = (flowId:string) => get(`https://${apiHost}/flow_definitions/${flowId}/steps`, null);
  
    return fetchSteps;
  };

export default useFetchSteps;
