// This file totally hacked together from https://github.com/jfeldstein/babel-plugin-export-default-module-exports
module.exports = ({types : t}) => ({
  visitor: {
    Program: {
      exit (path) {
        if (path.BABEL_PLUGIN_EXPORT_DEFAULT_MODULE_EXPORTS) {
          return
        }

        let hasExportDefault = false
        let hasExportNamed = false

        let namedExports = []

        
        path.get('body').forEach((path) => {
          // If there's already a default export, nothing to do
          if (path.isExportDefaultDeclaration()) {
            hasExportDefault = true
            return
          }

           // Find all existing named exports in the file
          if (path.isExportNamedDeclaration()) {
            const {node} = path;
            if (node.specifiers.length === 1 && node.specifiers[0].exported.name === 'default') {
              hasExportDefault = true
            } else {
              hasExportNamed = true

              let id;
              const {declaration = {}} = node;

              if(declaration) {
                if(declaration.id) {
                  id = declaration.id;
                }
                else if(declaration.declarations) {
                  const {declarations} = node.declaration
                  const [firstDeclaration = {}] = declarations

                  if(firstDeclaration.id) {
                    id = firstDeclaration.id
                  }
                }
              }

              if(id) {
                // Save the name of the export
                namedExports.push(id.name)
              }
            }
            return
          }
        })

        if (!hasExportDefault && hasExportNamed) {
          /*If we've got named exports and no default, turn them into something like:
          
              const namedExports = {
                  namedExport1,
                  namedExport2,
              };
              
              export default namedExports;
          */
          const objectProperties = namedExports.map (name => t.objectProperty(
            t.identifier(name),
            t.identifier(name),
            false, true
          ))

          const objDeclaration = t.variableDeclaration("const",
            [t.variableDeclarator(
              t.identifier("namedExports"),
              t.objectExpression(objectProperties)
            )]
          )

          const exportDefaultDeclaration = t.exportDefaultDeclaration(
            t.identifier("namedExports")
          )

          path.pushContainer("body", [
            objDeclaration,
            exportDefaultDeclaration
          ])
        }

        path.BABEL_PLUGIN_EXPORT_DEFAULT_MODULE_EXPORTS = true
      }
    }
  }
})