const urlParams = new URLSearchParams(window.location.search);
const auth_token = { authorization: urlParams.get('auth_token')??'', 'Content-Type': 'application/json' };
// const apiHost = "api.talkdeskstg.com";

const request = async(method = 'GET', url = '', options = {}) => {
    // try {
        const response = await fetch(url, {
          method,
          headers: auth_token,
          body: options ? JSON.stringify(options) : undefined
        });
    
        if (response.status !== 204) {
          return await response.json();
        }
    
        return {};
      // } catch (e) {
      //   // throw new Error(`Error at fetching data from ${url}: ${e}`);
      // }
    
    // if (method === 'GET') {
    //     return await fetch(url, {
    //         method,
    //         headers: auth_token,
    //     });
    // }
    // return await fetch(url, {
    //     method,
    //     headers: auth_token,
    //     body: JSON.stringify(options)
    // });
} 

const get = (url:string, options: any) => request('GET', url, options);
const put = (url:string, data: any, options:any) => request('PUT', url, { body: data, ...options });
const post = (url:string, data: any, options:any) => request('POST', url, { body: data, ...options });
const patch = (url:string, data: any, options:any) => request('PATCH', url, { body: data, ...options });
// const delete = (url:string, data: any, options:any) => request('DELETE', url, { body: data, ...options })

const useRequest = () => {
    return { get, put, post, patch };
}

export default useRequest;
