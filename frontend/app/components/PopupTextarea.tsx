import React, { ChangeEvent, KeyboardEvent, useState, useEffect } from "react";
import { Popover, PopoverTrigger, PopoverContent, List, ListItem } from "@chakra-ui/react";
import { AutoResizeTextarea } from "./AutoResizeTextarea";
import { commands } from "../utils/index"
interface PopupTextareaProps {
  value: string;
  placeholder?: string;
  onChange: (value: string) => void;
  onKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;
}

export const PopupTextarea = React.forwardRef<HTMLTextAreaElement, PopupTextareaProps>(({
  value,
  placeholder = "Input something...",
  onChange,
  onKeyDown,
}, ref) => {
  const [isOpen, setIsOpen] = useState(false);
  const [highlightedItem, setHighlightedItem] = useState<number | null>(null);

  const onValueChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    setTimeout(() => {
      e.target.focus();
    }, 100);
  }

  const onItemClick = (value: string) => {
    onChange(value + ' ');
    setHighlightedItem(null);
    setIsOpen(false);
  }

  const onEnterKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      if (highlightedItem !== null && isOpen) {
        e.preventDefault();
        onItemClick(commands[highlightedItem])
        console.log("onChange", commands[highlightedItem])
      } else {
        onKeyDown(e);
      }
    }

    if (e.key === "ArrowUp") {
      e.preventDefault();
      isOpen && highlightedItem && setHighlightedItem(highlightedItem - 1)
      onKeyDown(e);
    }

    if (e.key === "ArrowDown") {
      e.preventDefault();
      isOpen && typeof highlightedItem === 'number' && highlightedItem < 2 && setHighlightedItem(highlightedItem + 1)
    }
  }
    
  
  useEffect(() => {
    const matchCommands = value && commands.reduce((acc, command, index) => {
      const isMatch = command.includes(value);
      !acc && isMatch && setHighlightedItem(index);
      return acc || isMatch;
    }, false);
    if (matchCommands) {
      setIsOpen(true);
    } else {
      setIsOpen(false);
    }
  }, [value]);
  
  return (
    <Popover placement="top-start" isOpen={ isOpen }>
      <PopoverTrigger>
        <AutoResizeTextarea
          ref={ref}
          value={value}
          maxRows={5}
          marginRight={"56px"}
          placeholder={placeholder}
          borderColor={"rgb(58, 58, 61)"}
          onChange={onValueChange}
          onKeyDown={onEnterKeyDown}
          zIndex={100}
        />
      </PopoverTrigger>
      <PopoverContent>
        <List spacing={3}>
          {commands.map((command, index) => (
            <ListItem 
              style={{margin: 0, backgroundColor: highlightedItem === index ? "#ebf8ff" : undefined }} 
              key={index} 
              onMouseEnter={e => setHighlightedItem(index)}
              onMouseLeave={e => setHighlightedItem(null)}
              onClick={() => onItemClick(command)}
              >
              {command}
            </ListItem>
          ))}
        </List>
      </PopoverContent>
    </Popover>
  );
});

PopupTextarea.displayName
