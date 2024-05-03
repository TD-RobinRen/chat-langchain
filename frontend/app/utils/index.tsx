export const commands = ["/diff", "/explain", "/generate"];

// export const matchCommands = (text:string) => commands.reduce((acc, command, index) => {
//   const isMatch = text.includes(command);
//   return acc || isMatch;
// }, false);

export const matchCommands = (text: string): string | null => {
  for (let command of commands) {
    if (text.includes(command)) {
      return command;
    }
  }
  return null;
}


export const extractJson = (text: string) => /```json\n([\s\S]*?)\n```/ig.exec(text);

export const extractMessage = (str: string) => {
  return str.replace(/^(\/diff|\/explain|\/generate)\s/, '');
};

export const removeLinks = (obj: any): any => {
  if (Array.isArray(obj)) {
    return obj.map(removeLinks);
  } else if (obj !== null && typeof obj === 'object') {
    const newObj = { ...obj };
    delete newObj._links;
    Object.keys(newObj).forEach(key => {
      newObj[key] = removeLinks(newObj[key]);
    });
    return newObj;
  }
  return obj;
};
