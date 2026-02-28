import React, { Children, ReactNode } from 'react'
import {Box} from "@chakra-ui/react"


interface Props{
  children: ReactNode
}

//Bxox is a chakra component that returns a div
const GameCardContainer = ({children}: Props) => {
  return (
    <Box width="100%" borderRadius={10} overflow="hidden">
      {children}
    </Box>
    
  )
}

export default GameCardContainer
