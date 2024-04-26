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

export const jsonMarkdownRegex = /```json\n([\s\S]*?)\n```/g;

export const extractJson = (text:string) => jsonMarkdownRegex.exec(text);