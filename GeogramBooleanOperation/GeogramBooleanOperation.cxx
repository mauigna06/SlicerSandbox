/*
 *  Copyright (c) 2000-2022 Inria
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions are met:
 *
 *  * Redistributions of source code must retain the above copyright notice,
 *  this list of conditions and the following disclaimer.
 *  * Redistributions in binary form must reproduce the above copyright notice,
 *  this list of conditions and the following disclaimer in the documentation
 *  and/or other materials provided with the distribution.
 *  * Neither the name of the ALICE Project-Team nor the names of its
 *  contributors may be used to endorse or promote products derived from this
 *  software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 *  AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 *  IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 *  ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
 *  LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 *  CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 *  SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 *  INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 *  CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 *  ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *  POSSIBILITY OF SUCH DAMAGE.
 *
 *  Contact: Bruno Levy
 *
 *     https://www.inria.fr/fr/bruno-levy
 *
 *     Inria,
 *     Domaine de Voluceau,
 *     78150 Le Chesnay - Rocquencourt
 *     FRANCE
 *
 */

#if defined(_MSC_VER)
#pragma warning ( disable : 4786 )
#endif

#include "GeogramBooleanOperationCLP.h"

// VTK includes
// not needed

// MRML includes
#include "vtkMRMLModelNode.h"
#include "vtkMRMLModelStorageNode.h"


#include "geogram/basic/common.h"
#include "geogram/basic/logger.h"
#include "geogram/basic/command_line.h"
#include "geogram/basic/command_line_args.h"
#include "geogram/basic/stopwatch.h"
#include "geogram/mesh/mesh.h"
#include "geogram/mesh/mesh_io.h"
#include "geogram/mesh/mesh_repair.h"
#include "geogram/mesh/mesh_fill_holes.h"
#include "geogram/mesh/mesh_surface_intersection.h"
#include "geogram/mesh/mesh_geometry.h"
#include "geogram/mesh/mesh_remesh.h"

#include "algorithm"

namespace {
    using namespace GEO;

    /**
     * \brief Pre/Post-processes a mesh.
     * \details Triangulates the facets, collapses the small edges
     *  and removes self-intersections.
     */
    void fix_mesh_for_boolean_ops(Mesh& M) {
        mesh_repair(
            M,
            MeshRepairMode(
                MESH_REPAIR_COLOCATE | MESH_REPAIR_DUP_F
            ),
            1e-3*surface_average_edge_length(M)
        );
        tessellate_facets(M,3);
        mesh_remove_intersections(M);
    }
}


int main(int argc, char** argv) {
    using namespace GEO;

    // Needs to be called once.
    GEO::initialize(GEO::GEOGRAM_INSTALL_ALL);

    try {

        PARSE_ARGS;

        std::string A_filename = ModelA.c_str();
        std::string B_filename = ModelB.c_str();
        std::string output_filename = ResultingModel.c_str();

        Logger::div("Data I/O");

        Logger::out("I/O") << "Output = " << output_filename << std::endl;

        Mesh A;
        Mesh B;

        if(!mesh_load(A_filename,A)) {
            return 1;
        }

        if(!mesh_load(B_filename,B)) {
            return 1;
        }

        Mesh result;

        if(DoFixMeshes) {
            Logger::div("Pre-processing");
            //fix_mesh_for_boolean_ops(A); //this function does not work
            //fix_mesh_for_boolean_ops(B); //this function does not work
        }

        {
            Stopwatch Wboolean("Booleans");
            Logger::div("Boolean operation");
            //std::string op = BooleanOperation;
            std::string op = BooleanOperation.c_str();
            if(op == "union") {
                mesh_union(result, A, B);
            } else if(op == "intersection") {
                mesh_intersection(result, A, B);
            } else if(op == "difference") {
                mesh_difference(result, A, B);
            } else {
                Logger::err("Boolean") << op << ": invalid operation"
                                       << std::endl;
                return 1;
            }
        }

        if(DoFixMeshes) {
            Logger::div("Post-processing");
            //fix_mesh_for_boolean_ops(result); //this function does not work
        }

        Logger::div("Data I/O");

        if(output_filename != "none") {
            mesh_save(result, output_filename);
        }


    }
    catch(const std::exception& e) {
        std::cerr << "Received an exception: " << e.what() << std::endl;
        return 1;
    }

    Logger::out("") << "Everything OK, Returning status 0" << std::endl;
    return 0;
}