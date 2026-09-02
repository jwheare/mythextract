import {
  uniform,
  texture,
  uv,
  vec4,
  float,
  mix,
  select,
  Fn,
} from 'three/tsl';
import { Color } from 'three/webgpu';

export function shader (
  colorTex, shadowTex, darkCol, lightCol, darkFrac, lightFrac, transPoint
) {
  // Uniforms
  console.log(arguments);
  const colormap    = texture( colorTex ); // THREE.Texture
  const shadowmap   = texture( shadowTex ); // THREE.Texture
  const darkColor   = uniform( new Color(darkCol) );
  const lightColor  = uniform( new Color(lightCol) );
  const transitionPoint = uniform( transPoint );
  const darkScale   = uniform( darkFrac );
  const lightScale  = uniform( lightFrac );

  // Fragment logic as a TSL Fn node
  const shadingFn = Fn( () => {
    const color  = colormap.sample( uv() );
    const shadow = shadowmap.sample( uv() );

    const shade = shadow.r;

    // Dark branch
    const darkFraction = darkScale.mul(
      transitionPoint.sub( shade ).div( transitionPoint )
    );
    const darkResult = mix( color.rgb, darkColor, darkFraction );

    // Light branch
    const lightFraction = lightScale.mul(
      shade.sub( transitionPoint ).div( float( 1 ).sub( transitionPoint ) )
    );
    const lightResult = mix( color.rgb, lightColor, lightFraction );

    const isDark = shade.lessThanEqual( transitionPoint )
      .and( transitionPoint.greaterThan( float( 0 ) ) );

    const rgb = select( isDark, darkResult, lightResult );

    return vec4( rgb, float( 1 ) );
  } );
  return shadingFn();
}
