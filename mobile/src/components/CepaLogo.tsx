import React from 'react';
import { Image, StyleSheet, View } from 'react-native';

interface CepaLogoProps {
  size?: number;
}

export const CepaLogo: React.FC<CepaLogoProps> = ({ size = 32 }) => {
  return (
    <View style={[styles.container, { width: size, height: size }]}>
      <Image
        source={require('../../assets/logo.png')}
        style={[styles.logo, { width: size, height: size }]}
        resizeMode="contain"
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 7,
    backgroundColor: '#000000',
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.15)',
  },
  logo: {
    borderRadius: 6,
  },
});
